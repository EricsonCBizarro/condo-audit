<?php

namespace Tests\Feature\Console;

use App\Enums\JobType;
use App\Models\Condominium;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Storage;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

class DemoSeedCommandTest extends TestCase
{
    use RefreshDatabase;

    private string $dir;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('s3');
        config(['condo_audit.demo.email' => 'demo@example.com', 'condo_audit.demo.password' => 'demo-pass']);

        $this->dir = sys_get_temp_dir().'/demo-seed-'.uniqid();
        mkdir("{$this->dir}/condo/statements", 0777, true);
        file_put_contents("{$this->dir}/condo/statements/2025-02.pdf", "%PDF-1.4\n% february\n");
        file_put_contents("{$this->dir}/condo/convencao.pdf", "%PDF-1.4\n% convention\n");
        file_put_contents("{$this->dir}/manifest.json", json_encode(['condominiums' => [[
            'slug' => 'residencial-teste', 'name' => 'Residencial Teste', 'tax_id' => '00.000.000/0001-00',
            'city' => 'Cidade Exemplo', 'settings' => ['monthly_fee' => '950.00'],
            'documents' => [
                ['path' => 'condo/statements/2025-02.pdf', 'type' => 'financial_statement', 'title' => 'Balancete 02/2025', 'reference_period' => '2025-02'],
                ['path' => 'condo/convencao.pdf', 'type' => 'convention', 'title' => 'Convenção', 'reference_period' => null],
            ],
        ]]]));
    }

    #[Test]
    public function it_creates_the_tenant_the_demo_user_and_queues_every_document(): void
    {
        $this->artisan('demo:seed', ['path' => $this->dir])->assertSuccessful();

        $condominium = Condominium::where('slug', 'residencial-teste')->sole();
        $user = User::where('email', 'demo@example.com')->sole();
        $this->assertSame('owner', $user->roleIn($condominium)?->value);
        $this->assertSame(['2025-02-01', null], $condominium->documents()->orderBy('id')->pluck('reference_period')->map(fn ($d) => $d?->toDateString())->all());
        $this->assertCount(2, $this->jobs->messages);
        $this->assertSame(JobType::DocumentProcess, $this->jobs->messages[0]->type);
    }

    #[Test]
    public function running_it_twice_does_not_duplicate_anything(): void
    {
        $this->artisan('demo:seed', ['path' => $this->dir])->assertSuccessful();
        $this->artisan('demo:seed', ['path' => $this->dir])->expectsOutputToContain('0 new documents')->assertSuccessful();

        $this->assertSame(1, Condominium::count());
        $this->assertCount(2, $this->jobs->messages);
    }

    #[Test]
    public function it_fails_clearly_without_a_manifest(): void
    {
        $this->artisan('demo:seed', ['path' => '/nonexistent'])->expectsOutputToContain('No valid manifest.json')->assertFailed();
    }
}
