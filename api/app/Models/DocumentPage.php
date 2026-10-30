<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class DocumentPage extends Model
{
    protected $guarded = [];

    protected function casts(): array
    {
        return ['mean_confidence' => 'float'];
    }

    /** @return BelongsTo<Document, $this> */
    public function document(): BelongsTo
    {
        return $this->belongsTo(Document::class);
    }

    /** @return HasMany<PageLine, $this> */
    public function lines(): HasMany
    {
        return $this->hasMany(PageLine::class)->orderBy('line_number');
    }
}
