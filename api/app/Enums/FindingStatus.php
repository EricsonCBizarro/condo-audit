<?php

namespace App\Enums;

/**
 * Review workflow of a finding. The pipeline only ever creates findings as
 * `open`; every other transition is a human decision recorded in
 * finding_events.
 */
enum FindingStatus: string
{
    case Open = 'open';
    case Confirmed = 'confirmed';
    case Dismissed = 'dismissed';

    public function canTransitionTo(self $target): bool
    {
        return match ($this) {
            self::Open => $target !== self::Open,
            // Decisions can be revisited, but only by reopening first.
            self::Confirmed, self::Dismissed => $target === self::Open,
        };
    }

    /** @return list<string> */
    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }
}
