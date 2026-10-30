<?php

namespace App\Documents;

use App\Enums\DocumentStatus;
use App\Enums\DocumentType;
use App\Models\Condominium;
use App\Pipeline\PipelineDispatcher;
use Carbon\CarbonImmutable;
use Illuminate\Contracts\Filesystem\Filesystem;
use Illuminate\Database\UniqueConstraintViolationException;
use RuntimeException;

/**
 * Bronze layer entry point, shared by the upload endpoint and the
 * bulk-import command: hash → dedupe per condominium → store the original
 * bytes → record → enqueue processing.
 */
final class DocumentIngestionService
{
    public function __construct(
        private readonly Filesystem $storage,
        private readonly PipelineDispatcher $dispatcher,
    ) {}

    public function ingest(
        Condominium $condominium,
        string $localPath,
        string $originalFilename,
        DocumentType $type,
        ?string $title = null,
        ?CarbonImmutable $referencePeriod = null,
    ): IngestionResult {
        $sha256 = hash_file('sha256', $localPath);
        if ($sha256 === false) {
            throw new RuntimeException("Cannot read {$localPath}");
        }

        $existing = $condominium->documents()->where('sha256', $sha256)->first();
        if ($existing !== null) {
            return new IngestionResult($existing, duplicate: true, run: null);
        }

        $storageKey = sprintf('condominiums/%d/documents/%s.pdf', $condominium->id, $sha256);
        $stream = fopen($localPath, 'rb');
        if ($stream === false) {
            throw new RuntimeException("Cannot open {$localPath}");
        }

        try {
            if (! $this->storage->writeStream($storageKey, $stream)) {
                throw new RuntimeException("Could not store {$storageKey}");
            }
        } finally {
            if (is_resource($stream)) {
                fclose($stream);
            }
        }

        try {
            $document = $condominium->documents()->create([
                'type' => $type,
                'title' => $title ?? pathinfo($originalFilename, PATHINFO_FILENAME),
                'reference_period' => $referencePeriod?->startOfMonth(),
                'original_filename' => $originalFilename,
                'storage_key' => $storageKey,
                'mime_type' => 'application/pdf',
                'size_bytes' => (int) filesize($localPath),
                'sha256' => $sha256,
                'status' => DocumentStatus::Pending,
                'ingested_at' => now(),
            ]);
        } catch (UniqueConstraintViolationException) {
            // Concurrent upload of the same file won the race.
            return new IngestionResult(
                $condominium->documents()->where('sha256', $sha256)->firstOrFail(),
                duplicate: true,
                run: null,
            );
        }

        return new IngestionResult($document, duplicate: false, run: $this->dispatcher->processDocument($document));
    }
}
