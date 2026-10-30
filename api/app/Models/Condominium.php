<?php

namespace App\Models;

use Database\Factories\CondominiumFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Condominium extends Model
{
    /** @use HasFactory<CondominiumFactory> */
    use HasFactory;

    protected $table = 'condominiums';

    protected $fillable = ['name', 'slug', 'tax_id', 'city', 'settings'];

    protected function casts(): array
    {
        return ['settings' => 'array'];
    }

    public function getRouteKeyName(): string
    {
        return 'slug';
    }

    /** @return BelongsToMany<User, $this> */
    public function users(): BelongsToMany
    {
        return $this->belongsToMany(User::class)->withPivot('role')->withTimestamps();
    }

    /** @return HasMany<Document, $this> */
    public function documents(): HasMany
    {
        return $this->hasMany(Document::class);
    }

    /** @return HasMany<Finding, $this> */
    public function findings(): HasMany
    {
        return $this->hasMany(Finding::class);
    }

    /** @return HasMany<StatementEntry, $this> */
    public function statementEntries(): HasMany
    {
        return $this->hasMany(StatementEntry::class);
    }

    /** @return HasMany<PipelineRun, $this> */
    public function pipelineRuns(): HasMany
    {
        return $this->hasMany(PipelineRun::class);
    }
}
