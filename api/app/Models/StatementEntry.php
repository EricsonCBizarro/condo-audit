<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCondominium;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class StatementEntry extends Model
{
    use BelongsToCondominium;

    protected $guarded = [];

    protected function casts(): array
    {
        return [
            'entry_date' => 'date',
            'amount' => 'decimal:2',
            'balance' => 'decimal:2',
            'confidence' => 'float',
        ];
    }

    /** @return BelongsTo<Document, $this> */
    public function document(): BelongsTo
    {
        return $this->belongsTo(Document::class);
    }

    /** @return HasMany<EntryReceiptLink, $this> */
    public function receiptLinks(): HasMany
    {
        return $this->hasMany(EntryReceiptLink::class);
    }
}
