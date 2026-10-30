<?php

namespace App\Http\Resources;

use App\Models\Finding;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Finding */
class FindingResource extends JsonResource
{
    /** @return array<string, mixed> */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'rule_code' => $this->rule_code,
            'category' => $this->category->value,
            'severity' => $this->severity->value,
            'status' => $this->status->value,
            'title' => $this->title,
            'explanation' => $this->explanation,
            'amount' => $this->amount,
            'evidence' => $this->evidence,
            'is_active' => $this->is_active,
            'first_detected_at' => $this->first_detected_at->toIso8601String(),
            'last_detected_at' => $this->last_detected_at->toIso8601String(),
            'events' => FindingEventResource::collection($this->whenLoaded('events')),
        ];
    }
}
