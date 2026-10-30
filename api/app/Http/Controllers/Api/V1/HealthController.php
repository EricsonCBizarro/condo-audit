<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Facades\Storage;
use Throwable;

/**
 * Readiness probe: checks every dependency the API needs to accept work.
 */
class HealthController extends Controller
{
    public function __invoke(): JsonResponse
    {
        $checks = [
            'database' => $this->check(fn () => DB::select('select 1')),
            'redis' => $this->check(fn () => Redis::connection(config('condo_audit.pipeline.redis_connection'))->command('ping')),
            'storage' => $this->check(fn () => Storage::disk((string) config('condo_audit.documents_disk'))->directories('/')),
        ];

        $healthy = ! in_array(false, $checks, true);

        return response()->json(
            ['status' => $healthy ? 'ok' : 'degraded', 'checks' => array_map(fn (bool $ok) => $ok ? 'ok' : 'failing', $checks)],
            $healthy ? 200 : 503,
        );
    }

    private function check(callable $probe): bool
    {
        try {
            $probe();

            return true;
        } catch (Throwable $e) {
            report($e);

            return false;
        }
    }
}
