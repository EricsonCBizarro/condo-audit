<?php

namespace App\Enums;

enum JobType: string
{
    case DocumentProcess = 'document.process';
    case AuditRun = 'audit.run';

    /** @return list<string> */
    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }
}
