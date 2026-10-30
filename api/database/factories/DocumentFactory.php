<?php

namespace Database\Factories;

use App\Enums\DocumentStatus;
use App\Enums\DocumentType;
use App\Models\Condominium;
use App\Models\Document;
use Illuminate\Database\Eloquent\Factories\Factory;

/** @extends Factory<Document> */
class DocumentFactory extends Factory
{
    /** @return array<string, mixed> */
    public function definition(): array
    {
        $sha = hash('sha256', $this->faker->unique()->uuid());

        return [
            'condominium_id' => Condominium::factory(),
            'type' => DocumentType::FinancialStatement,
            'title' => 'Statement '.$this->faker->monthName(),
            'reference_period' => now()->startOfMonth(),
            'original_filename' => 'statement.pdf',
            'storage_key' => "documents/{$sha}.pdf",
            'mime_type' => 'application/pdf',
            'size_bytes' => 1024,
            'sha256' => $sha,
            'status' => DocumentStatus::Processed,
            'ingested_at' => now(),
            'metadata' => [],
        ];
    }
}
