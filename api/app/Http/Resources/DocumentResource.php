<?php

namespace App\Http\Resources;

use App\Models\Document;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Document */
class DocumentResource extends JsonResource
{
    /** @return array<string, mixed> */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'type' => $this->type->value,
            'title' => $this->title,
            'reference_period' => $this->reference_period?->format('Y-m'),
            'original_filename' => $this->original_filename,
            'sha256' => $this->sha256,
            'size_bytes' => $this->size_bytes,
            'page_count' => $this->page_count,
            'status' => $this->status->value,
            'text_source' => $this->text_source,
            'ingested_at' => $this->ingested_at->toIso8601String(),
            'processed_at' => $this->processed_at?->toIso8601String(),
        ];
    }
}
