<?php

namespace App\Enums;

enum DocumentType: string
{
    case FinancialStatement = 'financial_statement';
    case Budget = 'budget';
    case MeetingMinutes = 'meeting_minutes';
    case MeetingNotice = 'meeting_notice';
    case Bylaws = 'bylaws';
    case Convention = 'convention';
    case PenaltyNotice = 'penalty_notice';
    case Other = 'other';

    /** @return list<string> */
    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }
}
