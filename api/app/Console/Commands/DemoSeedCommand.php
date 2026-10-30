<?php

namespace App\Console\Commands;

use App\Documents\DocumentIngestionService;
use App\Enums\DocumentType;
use App\Enums\MembershipRole;
use App\Enums\PipelineRunStatus;
use App\Models\Condominium;
use App\Models\PipelineRun;
use App\Models\User;
use App\Pipeline\PipelineDispatcher;
use Carbon\CarbonImmutable;
use Illuminate\Console\Attributes\Description;
use Illuminate\Console\Attributes\Signature;
use Illuminate\Console\Command;
use Illuminate\Support\Collection;
use JsonException;

#[Signature('demo:seed {path : Directory with manifest.json written by `condo-audit synth generate`}
    {--wait : Wait for processing, then run the audit and print a summary}
    {--timeout=900 : Seconds to wait for the pipeline}')]
#[Description('Ingest the synthetic condominiums through the same service used by the upload API.')]
class DemoSeedCommand extends Command
{
    public function handle(DocumentIngestionService $ingestion, PipelineDispatcher $dispatcher): int
    {
        $base = rtrim((string) $this->argument('path'), '/');
        if (! is_file("{$base}/manifest.json")) {
            $this->error("No valid manifest.json in {$base}. Run `condo-audit synth generate` first.");

            return self::FAILURE;
        }
        try {
            /** @var array{condominiums: list<array{slug: string, name: string, tax_id: string, city: string, settings: array<string, mixed>, documents: list<array{path: string, type: string, title: string, reference_period: ?string}>}>} $manifest */
            $manifest = json_decode((string) file_get_contents("{$base}/manifest.json"), true, flags: JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            $this->error("No valid manifest.json in {$base}. Run `condo-audit synth generate` first.");

            return self::FAILURE;
        }

        $user = $this->demoUser();
        $condominiums = collect();
        $queued = 0;

        foreach ($manifest['condominiums'] as $spec) {
            $condominium = Condominium::updateOrCreate(
                ['slug' => $spec['slug']],
                ['name' => $spec['name'], 'tax_id' => $spec['tax_id'], 'city' => $spec['city'], 'settings' => $spec['settings']],
            );
            $condominium->users()->syncWithoutDetaching([$user->id => ['role' => MembershipRole::Owner->value]]);
            $condominiums->push($condominium);

            foreach ($spec['documents'] as $doc) {
                $result = $ingestion->ingest(
                    $condominium,
                    "{$base}/{$doc['path']}",
                    basename($doc['path']),
                    DocumentType::from($doc['type']),
                    $doc['title'],
                    $doc['reference_period'] ? CarbonImmutable::createFromFormat('!Y-m', $doc['reference_period']) ?: null : null,
                );
                $queued += $result->duplicate ? 0 : 1;
            }
            $this->info(sprintf('%s: %d documents', $condominium->name, count($spec['documents'])));
        }
        $this->line("{$queued} new documents queued for processing.");

        if (! $this->option('wait')) {
            return self::SUCCESS;
        }

        $deadline = time() + (int) $this->option('timeout');
        if (! $this->waitFor(fn () => $this->pending($condominiums, 'document.process'), $deadline, 'Processing documents')) {
            return self::FAILURE;
        }

        $condominiums->each(fn (Condominium $c) => $dispatcher->runAudit($c));
        if (! $this->waitFor(fn () => $this->pending($condominiums, 'audit.run'), $deadline, 'Running audit')) {
            return self::FAILURE;
        }

        $this->summary($condominiums);
        $this->newLine();
        $this->line('Dashboard: '.config('app.url').'  ·  login: '.$user->email);

        return self::SUCCESS;
    }

    private function demoUser(): User
    {
        $password = config('condo_audit.demo.password');
        if (! is_string($password) || $password === '') {
            $password = bin2hex(random_bytes(6));
            $this->warn("DEMO_USER_PASSWORD not set; generated one for this run: {$password}");
        }

        return User::updateOrCreate(
            ['email' => (string) config('condo_audit.demo.email')],
            ['name' => 'Demo Auditor', 'password' => $password],
        );
    }

    /**
     * @param  Collection<int, Condominium>  $condominiums
     */
    private function pending(Collection $condominiums, string $jobType): int
    {
        $failed = PipelineRun::query()
            ->whereIn('condominium_id', $condominiums->pluck('id'))
            ->where('job_type', $jobType)
            ->where('status', PipelineRunStatus::Dead)
            ->count();
        if ($failed > 0) {
            $this->warn("{$failed} {$jobType} job(s) failed permanently; see `make logs`.");
        }

        return PipelineRun::query()
            ->whereIn('condominium_id', $condominiums->pluck('id'))
            ->where('job_type', $jobType)
            ->whereIn('status', [PipelineRunStatus::Queued, PipelineRunStatus::Running])
            ->count();
    }

    private function waitFor(callable $pending, int $deadline, string $label): bool
    {
        $last = -1;
        while (($left = $pending()) > 0) {
            if ($left !== $last) {
                $this->line("  {$label}: {$left} job(s) left…");
                $last = $left;
            }
            if (time() > $deadline) {
                $this->error("Timed out while {$label}.");

                return false;
            }
            sleep(2);
        }
        $this->info("  {$label}: done.");

        return true;
    }

    /**
     * @param  Collection<int, Condominium>  $condominiums
     */
    private function summary(Collection $condominiums): void
    {
        foreach ($condominiums as $condominium) {
            $rows = $condominium->findings()
                ->where('is_active', true)
                ->selectRaw('rule_code, category, count(*) as total, coalesce(sum(amount), 0) as amount')
                ->groupBy('rule_code', 'category')
                ->orderBy('rule_code')
                ->toBase()
                ->get()
                ->map(fn (object $r) => [$r->rule_code, $r->category, $r->total, number_format((float) $r->amount, 2, ',', '.')]);

            $this->newLine();
            $this->info($condominium->name);
            $rows->isEmpty()
                ? $this->line('  No findings.')
                : $this->table(['Rule', 'Category', 'Findings', 'Amount (R$)'], $rows->all());
        }
    }
}
