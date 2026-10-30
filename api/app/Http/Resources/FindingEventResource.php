<?php

namespace App\Http\Resources;

use App\Models\FindingEvent;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin FindingEvent */
class FindingEventResource extends JsonResource
{
    /** @return array<string, mixed> */
    public function toArray(Request $request): array
    {
        return [
            'from_status' => $this->from_status->value,
            'to_status' => $this->to_status->value,
            'note' => $this->note,
            'user' => $this->user?->name,
            'created_at' => $this->created_at->toIso8601String(),
        ];
    }
}
