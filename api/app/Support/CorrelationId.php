<?php

namespace App\Support;

use Illuminate\Support\Facades\Context;
use Illuminate\Support\Str;

/**
 * Correlation id shared by the HTTP request, the log context, the queued
 * job and the worker logs, so one upload can be traced end to end.
 */
final class CorrelationId
{
    public const HEADER = 'X-Correlation-Id';

    private const CONTEXT_KEY = 'correlation_id';

    public static function current(): string
    {
        $id = Context::get(self::CONTEXT_KEY);
        if (is_string($id) && $id !== '') {
            return $id;
        }

        $id = self::generate();
        Context::add(self::CONTEXT_KEY, $id);

        return $id;
    }

    public static function set(string $id): void
    {
        Context::add(self::CONTEXT_KEY, $id);
    }

    public static function isValid(string $id): bool
    {
        return (bool) preg_match('/^[A-Za-z0-9._-]{8,64}$/', $id);
    }

    public static function generate(): string
    {
        return Str::lower((string) Str::ulid());
    }
}
