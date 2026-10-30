<?php

namespace Tests;

use App\Enums\MembershipRole;
use App\Models\Condominium;
use App\Models\User;
use App\Pipeline\InMemoryJobQueue;
use App\Pipeline\JobMessage;
use App\Pipeline\JobQueue;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Opis\JsonSchema\Errors\ErrorFormatter;
use Opis\JsonSchema\Validator;

abstract class TestCase extends BaseTestCase
{
    protected InMemoryJobQueue $jobs;

    protected function setUp(): void
    {
        parent::setUp();

        $this->jobs = new InMemoryJobQueue;
        $this->app->instance(JobQueue::class, $this->jobs);
        $this->withoutVite();
    }

    protected function memberOf(Condominium $condominium, MembershipRole $role = MembershipRole::Auditor): User
    {
        $user = User::factory()->create();
        $condominium->users()->attach($user, ['role' => $role->value]);

        return $user;
    }

    /**
     * Validates a published message against the JSON Schema shared with the
     * Python worker (contracts/job.schema.json).
     */
    protected function assertMatchesJobContract(JobMessage $message): void
    {
        $path = rtrim((string) config('condo_audit.contracts_path'), '/').'/job.schema.json';
        $this->assertFileExists($path, 'Shared job contract not found; set CONTRACTS_PATH.');

        $validator = new Validator;
        $validator->resolver()?->registerFile('https://github.com/condo-audit/contracts/job.schema.json', $path);
        $result = $validator->validate(json_decode($message->toJson()), 'https://github.com/condo-audit/contracts/job.schema.json');

        $error = $result->error();
        $this->assertTrue($result->isValid(), $error ? json_encode((new ErrorFormatter)->format($error)) ?: '' : '');
    }
}
