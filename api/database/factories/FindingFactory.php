<?php

namespace Database\Factories;

use App\Enums\FindingCategory;
use App\Enums\FindingSeverity;
use App\Enums\FindingStatus;
use App\Models\Condominium;
use App\Models\Finding;
use Illuminate\Database\Eloquent\Factories\Factory;

/** @extends Factory<Finding> */
class FindingFactory extends Factory
{
    /** @return array<string, mixed> */
    public function definition(): array
    {
        return [
            'condominium_id' => Condominium::factory(),
            'rule_code' => 'DUPLICATE_PAYMENT',
            'category' => FindingCategory::Irregularity,
            'severity' => FindingSeverity::Medium,
            'title' => 'Payment made twice',
            'explanation' => 'Same payee and amount paid twice within a few days.',
            'amount' => '150.00',
            'evidence' => [['document_id' => 1, 'page' => 1, 'excerpt' => 'PAGTO FORNECEDOR 150,00']],
            'fingerprint' => hash('sha256', $this->faker->unique()->uuid()),
            'status' => FindingStatus::Open,
            'is_active' => true,
            'first_detected_at' => now(),
            'last_detected_at' => now(),
        ];
    }

    public function severity(FindingSeverity $severity): static
    {
        return $this->state(['severity' => $severity]);
    }
}
