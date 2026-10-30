<?php

namespace App\Policies;

use App\Enums\MembershipRole;
use App\Models\Condominium;
use App\Models\User;

/**
 * Tenant boundary. Child resources (documents, findings, runs) are resolved
 * through scoped route bindings under the condominium, so authorizing the
 * condominium authorizes access to them.
 */
class CondominiumPolicy
{
    public function view(User $user, Condominium $condominium): bool
    {
        return $user->roleIn($condominium) !== null;
    }

    public function upload(User $user, Condominium $condominium): bool
    {
        return $this->canOperate($user, $condominium);
    }

    public function runAudit(User $user, Condominium $condominium): bool
    {
        return $this->canOperate($user, $condominium);
    }

    public function review(User $user, Condominium $condominium): bool
    {
        return $this->canOperate($user, $condominium);
    }

    private function canOperate(User $user, Condominium $condominium): bool
    {
        return in_array($user->roleIn($condominium), [MembershipRole::Owner, MembershipRole::Auditor], true);
    }
}
