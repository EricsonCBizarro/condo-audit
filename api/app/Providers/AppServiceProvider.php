<?php

namespace App\Providers;

use App\Documents\DocumentIngestionService;
use App\Pipeline\JobQueue;
use App\Pipeline\PipelineDispatcher;
use App\Pipeline\RedisJobQueue;
use Illuminate\Contracts\Foundation\Application;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(JobQueue::class, fn () => new RedisJobQueue(
            Redis::connection(config('condo_audit.pipeline.redis_connection')),
            (string) config('condo_audit.pipeline.jobs_key'),
        ));

        $this->app->singleton(PipelineDispatcher::class);

        $this->app->bind(DocumentIngestionService::class, fn (Application $app) => new DocumentIngestionService(
            Storage::disk((string) config('condo_audit.documents_disk')),
            $app->make(PipelineDispatcher::class),
        ));
    }

    public function boot(): void
    {
        Model::shouldBeStrict(! $this->app->isProduction());
    }
}
