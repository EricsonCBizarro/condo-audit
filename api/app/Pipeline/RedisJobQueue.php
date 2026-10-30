<?php

namespace App\Pipeline;

use Illuminate\Redis\Connections\Connection;

/**
 * Publishes to a plain Redis list consumed by the Python worker with a
 * reliable-queue pattern (BLMOVE into a per-worker processing list).
 * Laravel's own queue format is deliberately not used: the consumer is not
 * PHP, and a small explicit contract is easier to evolve on both sides.
 */
final class RedisJobQueue implements JobQueue
{
    public function __construct(
        private readonly Connection $redis,
        private readonly string $listKey,
    ) {}

    public function push(JobMessage $message): void
    {
        $this->redis->command('rpush', [$this->listKey, $message->toJson()]);
    }
}
