@extends('layouts.app', ['title' => $condominium->name])

@section('content')
    @php($s = $summary)
    <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
            <h1 class="text-xl font-semibold">{{ $condominium->name }}</h1>
            <p class="text-sm text-slate-500">{{ $condominium->city }} · CNPJ {{ $condominium->tax_id }} · last audit {{ $s['last_audit_at'] ? \Illuminate\Support\Carbon::parse($s['last_audit_at'])->diffForHumans() : 'never' }}</p>
        </div>
    </div>

    <div class="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        @foreach ([
            ['Documents processed', $s['documents']['processed'].' / '.$s['documents']['total']],
            ['Pages read by OCR', $ocrPages],
            ['Irregularities', $s['findings']['irregularities']],
            ['Amount involved', \App\Support\Format::brl($s['findings']['amount_at_stake'])],
        ] as [$label, $value])
            <div class="rounded-lg border border-slate-200 bg-white p-4">
                <div class="text-xs uppercase tracking-wide text-slate-500">{{ $label }}</div>
                <div class="mt-1 text-xl font-semibold tabular-nums">{{ $value }}</div>
            </div>
        @endforeach
    </div>

    <div class="mt-6 flex flex-wrap items-center gap-2 text-sm">
        <span class="text-slate-500">Show:</span>
        @foreach (['' => 'All', 'irregularity' => 'Irregularities', 'data_quality' => 'Review items'] as $value => $label)
            <a href="{{ route('condominiums.show', [$condominium, 'category' => $value ?: null]) }}"
               class="rounded-full px-3 py-1 ring-1 {{ request('category', '') === $value ? 'bg-indigo-600 text-white ring-indigo-600' : 'bg-white ring-slate-200 hover:ring-slate-300' }}">{{ $label }}</a>
        @endforeach
    </div>

    <div class="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table class="w-full text-sm">
            <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
                <th class="px-3 py-2">Severity</th>
                <th class="px-3 py-2">Finding</th>
                <th class="px-3 py-2">Rule</th>
                <th class="px-3 py-2">Period</th>
                <th class="px-3 py-2 text-right">Amount</th>
                <th class="px-3 py-2">Status</th>
            </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
            @forelse ($findings as $finding)
                <tr class="hover:bg-slate-50">
                    <td class="px-3 py-2.5"><x-severity :value="$finding->severity->value"/></td>
                    <td class="px-3 py-2.5"><a class="font-medium text-indigo-700 hover:underline" href="{{ route('findings.show', [$condominium, $finding]) }}">{{ $finding->title }}</a></td>
                    <td class="px-3 py-2.5 font-mono text-xs text-slate-500">{{ $finding->rule_code }}</td>
                    <td class="whitespace-nowrap px-3 py-2.5 tabular-nums">{{ $finding->period }}</td>
                    <td class="whitespace-nowrap px-3 py-2.5 text-right tabular-nums">{{ \App\Support\Format::brl($finding->amount) }}</td>
                    <td class="px-3 py-2.5"><x-status :value="$finding->status->value"/></td>
                </tr>
            @empty
                <tr><td colspan="6" class="px-3 py-8 text-center text-slate-500">No findings. Every rule passed.</td></tr>
            @endforelse
            </tbody>
        </table>
    </div>
@endsection
