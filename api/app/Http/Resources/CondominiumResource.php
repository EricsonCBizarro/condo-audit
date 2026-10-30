<?php

namespace App\Http\Resources;

use App\Models\Condominium;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Condominium */
class CondominiumResource extends JsonResource
{
    /** @return array<string, mixed> */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'slug' => $this->slug,
            'name' => $this->name,
            'city' => $this->city,
            'tax_id' => $this->tax_id,
        ];
    }
}
