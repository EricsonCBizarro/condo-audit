<?php

namespace App\Http\Controllers\Api\V1;

use App\Documents\DocumentIngestionService;
use App\Enums\DocumentType;
use App\Http\Controllers\Controller;
use App\Http\Requests\StoreDocumentRequest;
use App\Http\Resources\DocumentResource;
use App\Http\Resources\PipelineRunResource;
use App\Models\Condominium;
use App\Models\Document;
use Carbon\CarbonImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Symfony\Component\HttpFoundation\StreamedResponse;

class DocumentController extends Controller
{
    public function index(Request $request, Condominium $condominium): AnonymousResourceCollection
    {
        $this->authorize('view', $condominium);

        $documents = $condominium->documents()
            ->when($request->query('type'), fn ($q, $type) => $q->where('type', $type))
            ->when($request->query('status'), fn ($q, $status) => $q->where('status', $status))
            ->orderByDesc('reference_period')
            ->orderBy('id')
            ->paginate(min((int) $request->query('per_page', '25'), 100));

        return DocumentResource::collection($documents);
    }

    /**
     * Accepts the upload and returns 202: processing happens asynchronously.
     * Re-uploading identical bytes returns the existing document (200).
     */
    public function store(StoreDocumentRequest $request, Condominium $condominium, DocumentIngestionService $ingestion): JsonResponse
    {
        /** @var UploadedFile $file */
        $file = $request->file('file');
        $period = $request->filled('reference_period')
            ? CarbonImmutable::createFromFormat('!Y-m', $request->string('reference_period')->toString())?->startOfMonth()
            : null;

        $result = $ingestion->ingest(
            $condominium,
            $file->getRealPath(),
            $file->getClientOriginalName(),
            DocumentType::from($request->string('type')->toString()),
            $request->filled('title') ? $request->string('title')->toString() : null,
            $period ?: null,
        );

        return response()->json([
            'data' => new DocumentResource($result->document),
            'duplicate' => $result->duplicate,
            'run' => $result->run ? new PipelineRunResource($result->run) : null,
        ], $result->duplicate ? 200 : 202);
    }

    public function show(Condominium $condominium, Document $document): DocumentResource
    {
        $this->authorize('view', $condominium);

        return new DocumentResource($document);
    }

    public function file(Condominium $condominium, Document $document): StreamedResponse
    {
        $this->authorize('view', $condominium);

        return Storage::disk((string) config('condo_audit.documents_disk'))->response(
            $document->storage_key,
            $document->original_filename,
            ['Content-Type' => 'application/pdf'],
            'inline',
        );
    }
}
