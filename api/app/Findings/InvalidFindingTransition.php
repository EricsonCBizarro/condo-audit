<?php

namespace App\Findings;

use App\Enums\FindingStatus;
use DomainException;

final class InvalidFindingTransition extends DomainException
{
    public static function between(FindingStatus $from, FindingStatus $to): self
    {
        return new self("A finding cannot go from '{$from->value}' to '{$to->value}'.");
    }
}
