<?php

namespace App\Models;

use App\Enums\FindingCategory;
use App\Enums\FindingSeverity;
use App\Enums\FindingStatus;
use App\Models\Concerns\BelongsToCondominium;
use Database\Factories\FindingFactory;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Finding extends Model
{
    use BelongsToCondominium;

    /** @use HasFactory<FindingFactory> */
    use HasFactory;

    protected $guarded = [];

    protected function casts(): array
    {
        return [
            'category' => FindingCategory::class,
            'severity' => FindingSeverity::class,
            'status' => FindingStatus::class,
            'amount' => 'decimal:2',
            'evidence' => 'array',
            'is_active' => 'boolean',
            'first_detected_at' => 'datetime',
            'last_detected_at' => 'datetime',
        ];
    }

    /** @return HasMany<FindingEvent, $this> */
    public function events(): HasMany
    {
        return $this->hasMany(FindingEvent::class)->latest('created_at');
    }

    /**
     * @param  Builder<Finding>  $query
     * @return Builder<Finding>
     */
    public function scopeOrderBySeverity(Builder $query): Builder
    {
        return $query->orderByRaw(
            "case severity when 'critical' then 4 when 'high' then 3 when 'medium' then 2 else 1 end desc"
        );
    }
}
