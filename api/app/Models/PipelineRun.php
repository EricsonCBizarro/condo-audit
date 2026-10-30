<?php

namespace App\Models;

use App\Enums\JobType;
use App\Enums\PipelineRunStatus;
use App\Models\Concerns\BelongsToCondominium;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class PipelineRun extends Model
{
    use BelongsToCondominium;
    use HasUuids;

    protected $guarded = [];

    protected function casts(): array
    {
        return [
            'job_type' => JobType::class,
            'status' => PipelineRunStatus::class,
            'queued_at' => 'datetime',
            'started_at' => 'datetime',
            'finished_at' => 'datetime',
            'stats' => 'array',
        ];
    }

    /** @return BelongsTo<Document, $this> */
    public function document(): BelongsTo
    {
        return $this->belongsTo(Document::class);
    }

    public function isFinished(): bool
    {
        return in_array($this->status, [PipelineRunStatus::Succeeded, PipelineRunStatus::Failed, PipelineRunStatus::Dead], true);
    }
}
