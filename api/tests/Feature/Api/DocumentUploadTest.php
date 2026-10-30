<?php

namespace Tests\Feature\Api;

use App\Enums\JobType;
use App\Enums\MembershipRole;
use App\Models\Condominium;
use App\Support\CorrelationId;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Laravel\Sanctum\Sanctum;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

class DocumentUploadTest extends TestCase
{
    use RefreshDatabase;

    private Condominium $condominium;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('s3');
        $this->condominium = Condominium::factory()->create();
    }

    #[Test]
    public function an_upload_is_stored_recorded_and_queued(): void
    {
        Sanctum::actingAs($this->memberOf($this->condominium));

        $response = $this->postJson($this->url(), [
            'file' => $this->pdf('statement-2025-03.pdf'),
            'type' => 'financial_statement',
            'reference_period' => '2025-03',
        ], [CorrelationId::HEADER => 'test-correlation-01']);

        $response->assertAccepted()
            ->assertJsonPath('duplicate', false)
            ->assertJsonPath('data.type', 'financial_statement')
            ->assertJsonPath('data.reference_period', '2025-03')
            ->assertJsonPath('data.status', 'pending')
            ->assertJsonPath('run.status', 'queued')
            ->assertHeader(CorrelationId::HEADER, 'test-correlation-01');

        $document = $this->condominium->documents()->sole();
        Storage::disk('s3')->assertExists($document->storage_key);

        $this->assertCount(1, $this->jobs->messages);
        $message = $this->jobs->messages[0];
        $this->assertSame(JobType::DocumentProcess, $message->type);
        $this->assertSame(['document_id' => $document->id], $message->payload);
        $this->assertSame('test-correlation-01', $message->correlationId);
        $this->assertDatabaseHas('pipeline_runs', ['id' => $message->jobId, 'status' => 'queued', 'document_id' => $document->id]);
        $this->assertMatchesJobContract($message);
    }

    #[Test]
    public function the_reference_period_does_not_depend_on_todays_date(): void
    {
        // Regression: parsing '2025-02' on the 29th used to roll over to March.
        $this->travelTo(CarbonImmutable::parse('2026-01-29 10:00'));
        Sanctum::actingAs($this->memberOf($this->condominium));

        $this->postJson($this->url(), [
            'file' => $this->pdf('statement-2025-02.pdf'),
            'type' => 'financial_statement',
            'reference_period' => '2025-02',
        ])->assertAccepted()->assertJsonPath('data.reference_period', '2025-02');
    }

    #[Test]
    public function the_same_bytes_are_deduplicated_per_condominium(): void
    {
        Sanctum::actingAs($this->memberOf($this->condominium));
        $payload = ['type' => 'financial_statement'];

        $this->postJson($this->url(), [...$payload, 'file' => $this->pdf('a.pdf')])->assertAccepted();
        $this->postJson($this->url(), [...$payload, 'file' => $this->pdf('copy-of-a.pdf')])
            ->assertOk()
            ->assertJsonPath('duplicate', true)
            ->assertJsonPath('run', null);

        $this->assertSame(1, $this->condominium->documents()->count());
        $this->assertCount(1, $this->jobs->messages);
    }

    #[Test]
    public function viewers_cannot_upload(): void
    {
        Sanctum::actingAs($this->memberOf($this->condominium, MembershipRole::Viewer));

        $this->postJson($this->url(), ['type' => 'financial_statement', 'file' => $this->pdf('a.pdf')])
            ->assertForbidden();
        $this->assertSame([], $this->jobs->messages);
    }

    #[Test]
    public function it_validates_the_upload(): void
    {
        Sanctum::actingAs($this->memberOf($this->condominium));

        $this->postJson($this->url(), [
            'type' => 'spreadsheet',
            'file' => UploadedFile::fake()->create('notes.txt', 1, 'text/plain'),
            'reference_period' => '03/2025',
        ])->assertUnprocessable()->assertJsonValidationErrors(['type', 'file', 'reference_period']);
    }

    private function url(): string
    {
        return "/api/v1/condominiums/{$this->condominium->slug}/documents";
    }

    private function pdf(string $name): UploadedFile
    {
        // Same bytes regardless of the name, so dedupe can be tested.
        return UploadedFile::fake()->createWithContent($name, "%PDF-1.4\n% synthetic test file\n%%EOF\n");
    }
}
