<?php

namespace Tests\Feature\Api;

use App\Enums\FindingSeverity;
use App\Enums\MembershipRole;
use App\Models\Condominium;
use App\Models\Finding;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

class FindingReviewTest extends TestCase
{
    use RefreshDatabase;

    private Condominium $condominium;

    protected function setUp(): void
    {
        parent::setUp();
        $this->condominium = Condominium::factory()->create();
    }

    #[Test]
    public function findings_are_listed_most_severe_first_and_filterable(): void
    {
        Finding::factory()->for($this->condominium)->severity(FindingSeverity::Low)->create(['rule_code' => 'MISSING_RECEIPT']);
        Finding::factory()->for($this->condominium)->severity(FindingSeverity::Critical)->create();
        Finding::factory()->for($this->condominium)->severity(FindingSeverity::Medium)->create(['is_active' => false]);
        Sanctum::actingAs($this->memberOf($this->condominium, MembershipRole::Viewer));

        $this->getJson($this->url())
            ->assertOk()
            ->assertJsonCount(2, 'data')
            ->assertJsonPath('data.0.severity', 'critical')
            ->assertJsonPath('data.1.severity', 'low');

        $this->getJson($this->url().'?rule=MISSING_RECEIPT')->assertJsonCount(1, 'data');
        $this->getJson($this->url().'?include_inactive=1')->assertJsonCount(3, 'data');
    }

    #[Test]
    public function an_auditor_confirms_a_finding_and_the_decision_is_logged(): void
    {
        $finding = Finding::factory()->for($this->condominium)->create();
        $auditor = $this->memberOf($this->condominium);
        Sanctum::actingAs($auditor);

        $this->patchJson($this->url($finding), ['status' => 'confirmed', 'note' => 'Bank statement checked.'])
            ->assertOk()
            ->assertJsonPath('data.status', 'confirmed')
            ->assertJsonPath('data.events.0.to_status', 'confirmed')
            ->assertJsonPath('data.events.0.note', 'Bank statement checked.')
            ->assertJsonPath('data.events.0.user', $auditor->name);

        $this->assertDatabaseHas('finding_events', [
            'finding_id' => $finding->id, 'user_id' => $auditor->id, 'from_status' => 'open', 'to_status' => 'confirmed',
        ]);
    }

    #[Test]
    public function a_decided_finding_must_be_reopened_before_changing_its_decision(): void
    {
        $finding = Finding::factory()->for($this->condominium)->create(['status' => 'dismissed']);
        Sanctum::actingAs($this->memberOf($this->condominium));

        $this->patchJson($this->url($finding), ['status' => 'confirmed'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('status');

        $this->patchJson($this->url($finding), ['status' => 'open'])->assertOk()->assertJsonPath('data.status', 'open');
    }

    #[Test]
    public function viewers_cannot_review(): void
    {
        $finding = Finding::factory()->for($this->condominium)->create();
        Sanctum::actingAs($this->memberOf($this->condominium, MembershipRole::Viewer));

        $this->patchJson($this->url($finding), ['status' => 'dismissed'])->assertForbidden();
        $this->assertSame('open', $finding->fresh()?->status->value);
    }

    private function url(?Finding $finding = null): string
    {
        return "/api/v1/condominiums/{$this->condominium->slug}/findings".($finding ? "/{$finding->id}" : '');
    }
}
