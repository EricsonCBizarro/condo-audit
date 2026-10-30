<?php

namespace App\Pipeline;

use App\Enums\JobType;
use App\Enums\PipelineRunStatus;
use App\Models\Condominium;
use App\Models\Document;
use App\Models\PipelineRun;
use App\Support\CorrelationId;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Creates the pipeline_runs row and publishes the job. The row is committed
 * before the message is published, so the worker never sees a job whose run
 * does not exist yet.
 */
final class PipelineDispatcher
{
    public function __construct(private readonly JobQueue $queue) {}

    public function processDocument(Document $document, bool $force = false): PipelineRun
    {
        $payload = ['document_id' => $document->id];
        if ($force) {
            $payload['force'] = true;
        }

        return $this->dispatch(JobType::DocumentProcess, $document->condominium()->firstOrFail(), $payload, $document);
    }

    /**
     * @param  list<string>  $rules  empty = every registered rule
     */
    public function runAudit(Condominium $condominium, array $rules = []): PipelineRun
    {
        return $this->dispatch(JobType::AuditRun, $condominium, $rules === [] ? [] : ['rules' => $rules]);
    }

    /**
     * @param  array<string, mixed>  $payload
     */
    private function dispatch(JobType $type, Condominium $condominium, array $payload, ?Document $document = null): PipelineRun
    {
        $run = DB::transaction(fn () => PipelineRun::create([
            'id' => (string) Str::uuid(),
            'condominium_id' => $condominium->id,
            'document_id' => $document?->id,
            'job_type' => $type,
            'status' => PipelineRunStatus::Queued,
            'correlation_id' => CorrelationId::current(),
            'queued_at' => now(),
        ]));

        $this->queue->push(new JobMessage(
            jobId: $run->id,
            type: $type,
            condominiumId: $condominium->id,
            correlationId: $run->correlation_id,
            enqueuedAt: $run->queued_at,
            payload: $payload,
        ));

        return $run;
    }
}
