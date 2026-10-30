<?php

namespace Tests\Unit;

use App\Enums\FindingStatus;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\TestCase;

class FindingStatusTest extends TestCase
{
    /** @return iterable<string, array{FindingStatus, FindingStatus, bool}> */
    public static function transitions(): iterable
    {
        yield 'open → confirmed' => [FindingStatus::Open, FindingStatus::Confirmed, true];
        yield 'open → dismissed' => [FindingStatus::Open, FindingStatus::Dismissed, true];
        yield 'open → open' => [FindingStatus::Open, FindingStatus::Open, false];
        yield 'confirmed → open' => [FindingStatus::Confirmed, FindingStatus::Open, true];
        yield 'confirmed → dismissed' => [FindingStatus::Confirmed, FindingStatus::Dismissed, false];
        yield 'dismissed → confirmed' => [FindingStatus::Dismissed, FindingStatus::Confirmed, false];
        yield 'dismissed → open' => [FindingStatus::Dismissed, FindingStatus::Open, true];
    }

    #[Test]
    #[DataProvider('transitions')]
    public function it_enforces_the_review_workflow(FindingStatus $from, FindingStatus $to, bool $allowed): void
    {
        $this->assertSame($allowed, $from->canTransitionTo($to));
    }
}
