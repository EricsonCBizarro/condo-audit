<?php

namespace App\Http\Resources;

use App\Models\PipelineRun;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin PipelineRun */
class PipelineRunResource extends JsonResource
{
    /** @return array<string, mixed> */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'job_type' => $this->job_type->value,
            'status' => $this->status->value,
            'document_id' => $this->document_id,
            'attempts' => $this->attempts,
            'correlation_id' => $this->correlation_id,
            'queued_at' => $this->queued_at->toIso8601String(),
            'started_at' => $this->started_at?->toIso8601String(),
            'finished_at' => $this->finished_at?->toIso8601String(),
            'error' => $this->error,
            'stats' => $this->stats,
        ];
    }
}
