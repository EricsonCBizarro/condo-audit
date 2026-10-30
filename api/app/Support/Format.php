<?php

namespace App\Support;

final class Format
{
    public static function brl(float|int|string|null $value): string
    {
        return $value === null ? '—' : 'R$ '.number_format((float) $value, 2, ',', '.');
    }

    public static function label(string $code): string
    {
        return ucfirst(strtolower(str_replace('_', ' ', $code)));
    }
}
