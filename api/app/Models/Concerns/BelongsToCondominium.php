<?php

namespace App\Models\Concerns;

use App\Models\Condominium;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * Every tenant-owned record carries condominium_id. Access is always scoped
 * through the parent condominium (scoped route bindings + policies), never by
 * a global "current tenant" singleton.
 */
trait BelongsToCondominium
{
    /** @return BelongsTo<Condominium, $this> */
    public function condominium(): BelongsTo
    {
        return $this->belongsTo(Condominium::class);
    }
}
