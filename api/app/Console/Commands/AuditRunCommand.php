<?php

namespace App\Console\Commands;

use App\Models\Condominium;
use App\Pipeline\PipelineDispatcher;
use Illuminate\Console\Attributes\Description;
use Illuminate\Console\Attributes\Signature;
use Illuminate\Console\Command;

#[Signature('audit:run {condominium? : Condominium slug (all when omitted)} {--rule=* : Only these rule codes}')]
#[Description('Queue an audit run for one or every condominium.')]
class AuditRunCommand extends Command
{
    public function handle(PipelineDispatcher $dispatcher): int
    {
        $slug = $this->argument('condominium');
        $condominiums = Condominium::query()->when($slug, fn ($q, $s) => $q->where('slug', $s))->get();

        if ($condominiums->isEmpty()) {
            $this->error('No condominium found.');

            return self::FAILURE;
        }

        /** @var list<string> $rules */
        $rules = array_values((array) $this->option('rule'));
        foreach ($condominiums as $condominium) {
            $run = $dispatcher->runAudit($condominium, $rules);
            $this->line("{$condominium->slug}: audit queued ({$run->id})");
        }

        return self::SUCCESS;
    }
}
