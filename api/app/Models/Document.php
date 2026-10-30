<?php

namespace App\Models;

use App\Enums\DocumentStatus;
use App\Enums\DocumentType;
use App\Models\Concerns\BelongsToCondominium;
use Database\Factories\DocumentFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Document extends Model
{
    use BelongsToCondominium;

    /** @use HasFactory<DocumentFactory> */
    use HasFactory;

    protected $fillable = [
        'condominium_id', 'type', 'title', 'reference_period', 'original_filename', 'storage_key',
        'mime_type', 'size_bytes', 'sha256', 'page_count', 'status', 'text_source', 'ingested_at',
        'processed_at', 'metadata',
    ];

    protected function casts(): array
    {
        return [
            'type' => DocumentType::class,
            'status' => DocumentStatus::class,
            'reference_period' => 'date',
            'ingested_at' => 'datetime',
            'processed_at' => 'datetime',
            'metadata' => 'array',
        ];
    }

    /** @return HasMany<DocumentPage, $this> */
    public function pages(): HasMany
    {
        return $this->hasMany(DocumentPage::class)->orderBy('page_number');
    }

    /** @return HasMany<PipelineRun, $this> */
    public function pipelineRuns(): HasMany
    {
        return $this->hasMany(PipelineRun::class);
    }
}
