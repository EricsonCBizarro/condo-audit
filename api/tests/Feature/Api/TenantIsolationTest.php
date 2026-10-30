<?php

namespace Tests\Feature\Api;

use App\Models\Condominium;
use App\Models\Document;
use App\Models\Finding;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

class TenantIsolationTest extends TestCase
{
    use RefreshDatabase;

    #[Test]
    public function a_user_only_lists_condominiums_they_belong_to(): void
    {
        $mine = Condominium::factory()->create();
        Condominium::factory()->create();
        Sanctum::actingAs($this->memberOf($mine));

        $this->getJson('/api/v1/condominiums')
            ->assertOk()
            ->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0.slug', $mine->slug);
    }

    #[Test]
    public function a_user_cannot_read_another_condominium(): void
    {
        $mine = Condominium::factory()->create();
        $other = Condominium::factory()->create();
        Sanctum::actingAs($this->memberOf($mine));

        $this->getJson("/api/v1/condominiums/{$other->slug}")->assertForbidden();
        $this->getJson("/api/v1/condominiums/{$other->slug}/findings")->assertForbidden();
        $this->getJson("/api/v1/condominiums/{$other->slug}/documents")->assertForbidden();
    }

    #[Test]
    public function child_resources_cannot_be_reached_through_a_different_condominium(): void
    {
        $mine = Condominium::factory()->create();
        $other = Condominium::factory()->create();
        $foreignDocument = Document::factory()->for($other)->create();
        $foreignFinding = Finding::factory()->for($other)->create();
        Sanctum::actingAs($this->memberOf($mine));

        // The ids exist, but not under this condominium: scoped bindings 404.
        $this->getJson("/api/v1/condominiums/{$mine->slug}/documents/{$foreignDocument->id}")->assertNotFound();
        $this->getJson("/api/v1/condominiums/{$mine->slug}/findings/{$foreignFinding->id}")->assertNotFound();
        $this->patchJson("/api/v1/condominiums/{$mine->slug}/findings/{$foreignFinding->id}", ['status' => 'dismissed'])
            ->assertNotFound();
    }
}
