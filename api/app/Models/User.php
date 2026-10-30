<?php

namespace App\Models;

use App\Enums\MembershipRole;
use Database\Factories\UserFactory;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Hidden;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

#[Fillable(['name', 'email', 'password'])]
#[Hidden(['password', 'remember_token'])]
class User extends Authenticatable
{
    use HasApiTokens;

    /** @use HasFactory<UserFactory> */
    use HasFactory;

    use Notifiable;

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password' => 'hashed',
        ];
    }

    /** @return BelongsToMany<Condominium, $this> */
    public function condominiums(): BelongsToMany
    {
        return $this->belongsToMany(Condominium::class)->withPivot('role')->withTimestamps();
    }

    public function roleIn(Condominium $condominium): ?MembershipRole
    {
        $role = $this->condominiums()
            ->whereKey($condominium->getKey())
            ->first()
            ?->getRelationValue('pivot')
            ?->getAttribute('role');

        return is_string($role) ? MembershipRole::from($role) : null;
    }
}
