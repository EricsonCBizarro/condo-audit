<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCondominium;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/** Gold-layer entity written by the pipeline; read-only for the API. */
class BylawClause extends Model
{
    use BelongsToCondominium;

    protected $guarded = [];

    /** @return BelongsTo<Document, $this> */
    public function document(): BelongsTo
    {
        return $this->belongsTo(Document::class);
    }
}
