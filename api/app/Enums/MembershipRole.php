<?php

namespace App\Enums;

enum MembershipRole: string
{
    case Owner = 'owner';
    case Auditor = 'auditor';
    case Viewer = 'viewer';

    /** @return list<string> */
    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }
}
