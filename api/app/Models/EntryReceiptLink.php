<?php

namespace App\Models;

use App\Enums\LinkStatus;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class EntryReceiptLink extends Model
{
    protected $guarded = [];

    protected function casts(): array
    {
        return ['status' => LinkStatus::class, 'score' => 'float'];
    }

    /** @return BelongsTo<StatementEntry, $this> */
    public function statementEntry(): BelongsTo
    {
        return $this->belongsTo(StatementEntry::class);
    }

    /** @return BelongsTo<Receipt, $this> */
    public function receipt(): BelongsTo
    {
        return $this->belongsTo(Receipt::class);
    }
}
