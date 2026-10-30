<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

class AuthTokenTest extends TestCase
{
    use RefreshDatabase;

    #[Test]
    public function it_issues_a_token_for_valid_credentials(): void
    {
        $user = User::factory()->create(['password' => 'correct-horse']);

        $this->postJson('/api/v1/auth/token', [
            'email' => $user->email,
            'password' => 'correct-horse',
            'device_name' => 'cli',
        ])->assertCreated()->assertJsonStructure(['token', 'token_type']);
    }

    #[Test]
    public function it_rejects_invalid_credentials(): void
    {
        $user = User::factory()->create(['password' => 'correct-horse']);

        $this->postJson('/api/v1/auth/token', [
            'email' => $user->email,
            'password' => 'wrong',
            'device_name' => 'cli',
        ])->assertUnprocessable()->assertJsonValidationErrors('email');
    }

    #[Test]
    public function protected_endpoints_require_a_token(): void
    {
        $this->getJson('/api/v1/condominiums')->assertUnauthorized();
    }
}
