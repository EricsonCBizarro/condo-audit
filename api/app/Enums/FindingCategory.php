<?php

namespace App\Enums;

enum FindingCategory: string
{
    case Irregularity = 'irregularity';
    case DataQuality = 'data_quality';

    /** @return list<string> */
    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }
}
