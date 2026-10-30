<?php

namespace App\Enums;

enum LinkStatus: string
{
    case Suggested = 'suggested';
    case Confirmed = 'confirmed';
    case Rejected = 'rejected';

    /** @return list<string> */
    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }
}
