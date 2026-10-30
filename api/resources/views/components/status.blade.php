@props(['value'])
@php
    $styles = [
        'open' => 'text-slate-600 bg-white ring-slate-300',
        'confirmed' => 'text-rose-700 bg-rose-50 ring-rose-200',
        'dismissed' => 'text-emerald-700 bg-emerald-50 ring-emerald-200',
    ];
@endphp
<span class="inline-flex rounded-full px-2 py-0.5 text-xs ring-1 {{ $styles[$value] ?? $styles['open'] }}">{{ $value }}</span>
