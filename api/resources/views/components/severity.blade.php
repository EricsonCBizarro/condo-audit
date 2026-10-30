@props(['value'])
@php
    $styles = [
        'critical' => 'bg-rose-600 text-white',
        'high' => 'bg-orange-100 text-orange-800 ring-1 ring-orange-200',
        'medium' => 'bg-amber-50 text-amber-800 ring-1 ring-amber-200',
        'low' => 'bg-slate-100 text-slate-600 ring-1 ring-slate-200',
    ];
@endphp
<span class="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium {{ $styles[$value] ?? $styles['low'] }}">{{ $value }}</span>
