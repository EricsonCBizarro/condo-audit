<?php

namespace App\Http\Resources;

use App\Models\StatementEntry;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin StatementEntry */
class StatementEntryResource extends JsonResource
{
    /** @return array<string, mixed> */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'document_id' => $this->document_id,
            'page_number' => $this->page_number,
            'kind' => $this->kind,
            'entry_date' => $this->entry_date?->toDateString(),
            'description' => $this->description,
            'amount' => $this->amount,
            'balance' => $this->balance,
            'category' => $this->category,
            'reconciliation' => $this->reconciliation,
            'confidence' => $this->confidence,
        ];
    }
}
