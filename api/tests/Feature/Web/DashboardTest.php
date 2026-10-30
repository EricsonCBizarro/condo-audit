<?php

namespace Tests\Feature\Web;

use App\Enums\FindingSeverity;
use App\Enums\MembershipRole;
use App\Models\Condominium;
use App\Models\Document;
use App\Models\Finding;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

class DashboardTest extends TestCase
{
    use RefreshDatabase;

    #[Test]
    public function guests_are_sent_to_the_login_page(): void
    {
        $this->get('/condominiums')->assertRedirect('/login');
        $this->get('/login')->assertOk()->assertSee('Log in');
    }

    #[Test]
    public function a_user_logs_in_with_valid_credentials(): void
    {
        $user = User::factory()->create(['password' => 'secret-pass']);

        $this->post('/login', ['email' => $user->email, 'password' => 'secret-pass'])->assertRedirect('/condominiums');
        $this->assertAuthenticatedAs($user);
    }

    #[Test]
    public function the_overview_lists_findings_most_severe_first(): void
    {
        $condominium = Condominium::factory()->create(['name' => 'Residencial Teste']);
        Finding::factory()->for($condominium)->severity(FindingSeverity::Low)->create(['title' => 'Low thing']);
        Finding::factory()->for($condominium)->severity(FindingSeverity::High)->create(['title' => 'Serious thing']);

        $this->actingAs($this->memberOf($condominium, MembershipRole::Viewer))
            ->get("/condominiums/{$condominium->slug}")
            ->assertOk()
            ->assertSeeInOrder(['Serious thing', 'Low thing']);

        $this->get('/condominiums')->assertOk()->assertSee('Residencial Teste')->assertSee('2 irregularities');
    }

    #[Test]
    public function an_auditor_reviews_a_finding_from_the_dashboard(): void
    {
        $condominium = Condominium::factory()->create();
        $finding = Finding::factory()->for($condominium)->create();
        $auditor = $this->memberOf($condominium);

        $this->actingAs($auditor)
            ->get("/condominiums/{$condominium->slug}/findings/{$finding->id}")
            ->assertOk()
            ->assertSee('Confirm');

        $this->post("/condominiums/{$condominium->slug}/findings/{$finding->id}/review", ['status' => 'dismissed', 'note' => 'Explained by the manager.'])
            ->assertRedirect("/condominiums/{$condominium->slug}/findings/{$finding->id}");

        $this->assertSame('dismissed', $finding->fresh()?->status->value);
        $this->get("/condominiums/{$condominium->slug}/findings/{$finding->id}")->assertSee('Explained by the manager.')->assertSee('Reopen');
    }

    #[Test]
    public function viewers_see_findings_but_cannot_review_them(): void
    {
        $condominium = Condominium::factory()->create();
        $finding = Finding::factory()->for($condominium)->create();
        $this->actingAs($this->memberOf($condominium, MembershipRole::Viewer));

        $this->get("/condominiums/{$condominium->slug}/findings/{$finding->id}")->assertOk()->assertDontSee('Confirm');
        $this->post("/condominiums/{$condominium->slug}/findings/{$finding->id}/review", ['status' => 'dismissed'])->assertForbidden();
    }

    #[Test]
    public function pages_of_another_condominium_are_forbidden(): void
    {
        $mine = Condominium::factory()->create();
        $other = Condominium::factory()->create();
        $document = Document::factory()->for($other)->create();
        $this->actingAs($this->memberOf($mine));

        $this->get("/condominiums/{$other->slug}")->assertForbidden();
        $this->get("/condominiums/{$other->slug}/documents/{$document->id}")->assertForbidden();
        $this->get("/condominiums/{$mine->slug}/documents/{$document->id}")->assertNotFound();
    }

    #[Test]
    public function documents_and_statements_pages_render(): void
    {
        $condominium = Condominium::factory()->create();
        $document = Document::factory()->for($condominium)->create(['title' => 'Balancete 03/2025', 'page_count' => 2]);
        $this->actingAs($this->memberOf($condominium, MembershipRole::Viewer));

        $this->get("/condominiums/{$condominium->slug}/documents")->assertOk()->assertSee('Balancete 03/2025');
        $this->get("/condominiums/{$condominium->slug}/documents/{$document->id}?page=1")->assertOk()->assertSee('What the pipeline read');
        $this->get("/condominiums/{$condominium->slug}/statements")->assertOk()->assertSee('Balancete 03/2025');
    }
}
