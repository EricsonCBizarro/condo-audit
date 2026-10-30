<?php

namespace Tests\Feature\Api;

use App\Enums\JobType;
use App\Enums\MembershipRole;
use App\Models\Condominium;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

class AuditRunTest extends TestCase
{
    use RefreshDatabase;

    #[Test]
    public function an_auditor_can_queue_an_audit_run(): void
    {
        $condominium = Condominium::factory()->create();
        Sanctum::actingAs($this->memberOf($condominium));

        $response = $this->postJson("/api/v1/condominiums/{$condominium->slug}/audit-runs", ['rules' => ['DUPLICATE_PAYMENT']])
            ->assertAccepted()
            ->assertJsonPath('data.job_type', 'audit.run')
            ->assertJsonPath('data.status', 'queued');

        $message = $this->jobs->messages[0];
        $this->assertSame(JobType::AuditRun, $message->type);
        $this->assertSame(['rules' => ['DUPLICATE_PAYMENT']], $message->payload);
        $this->assertMatchesJobContract($message);

        $this->getJson("/api/v1/condominiums/{$condominium->slug}/pipeline-runs/{$response->json('data.id')}")
            ->assertOk()
            ->assertJsonPath('data.id', $message->jobId);
    }

    #[Test]
    public function an_audit_of_every_rule_sends_an_empty_object_payload(): void
    {
        $condominium = Condominium::factory()->create();
        Sanctum::actingAs($this->memberOf($condominium));

        $this->postJson("/api/v1/condominiums/{$condominium->slug}/audit-runs")->assertAccepted();

        $this->assertStringContainsString('"payload":{}', $this->jobs->messages[0]->toJson());
        $this->assertMatchesJobContract($this->jobs->messages[0]);
    }

    #[Test]
    public function viewers_cannot_queue_audits(): void
    {
        $condominium = Condominium::factory()->create();
        Sanctum::actingAs($this->memberOf($condominium, MembershipRole::Viewer));

        $this->postJson("/api/v1/condominiums/{$condominium->slug}/audit-runs")->assertForbidden();
    }
}
