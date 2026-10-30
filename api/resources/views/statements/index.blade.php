@extends('layouts.app', ['title' => 'Statements'])

@section('content')
    <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
            <h1 class="text-xl font-semibold">Bank statements</h1>
            <p class="mt-1 text-sm text-slate-500">Every line is reconciled against the running balance and matched to its receipt.</p>
        </div>
        <form class="text-sm">
            <select name="document" onchange="this.form.submit()" class="rounded-md border border-slate-300 bg-white px-2 py-1.5">
                @foreach ($periods as $p)
                    <option value="{{ $p->id }}" @selected($selected?->id === $p->id)>{{ $p->title }}</option>
                @endforeach
            </select>
        </form>
    </div>

    <div class="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table class="w-full text-sm">
            <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr><th class="px-3 py-2">Date</th><th class="px-3 py-2">Description</th><th class="px-3 py-2">Category</th><th class="px-3 py-2 text-right">Amount</th><th class="px-3 py-2 text-right">Balance</th><th class="px-3 py-2">Check</th><th class="px-3 py-2">Receipt</th><th class="px-3 py-2 text-right">OCR</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
            @foreach ($entries as $e)
                <tr class="{{ $e->reconciliation === 'inconsistent' ? 'bg-rose-50' : '' }}">
                    <td class="px-3 py-1.5 tabular-nums">{{ $e->entry_date?->format('d/m') }}</td>
                    <td class="px-3 py-1.5">{{ $e->description }}</td>
                    <td class="px-3 py-1.5 text-xs text-slate-500">{{ $e->category }}</td>
                    <td class="px-3 py-1.5 text-right tabular-nums {{ (float) $e->amount < 0 ? 'text-rose-700' : 'text-emerald-700' }}">{{ $e->amount !== null ? number_format((float) $e->amount, 2, ',', '.') : '' }}</td>
                    <td class="px-3 py-1.5 text-right tabular-nums">{{ $e->balance !== null ? number_format((float) $e->balance, 2, ',', '.') : '' }}</td>
                    <td class="px-3 py-1.5 text-xs">
                        @if ($e->reconciliation === 'ok')<span class="text-emerald-700">✓</span>
                        @elseif ($e->reconciliation === 'inconsistent')<span class="font-medium text-rose-700">breaks chain</span>
                        @else<span class="text-slate-400">{{ $e->reconciliation }}</span>@endif
                    </td>
                    <td class="px-3 py-1.5 text-xs">
                        @if ($e->kind === 'transaction' && (float) $e->amount < 0)
                            {!! $e->receiptLinks->isNotEmpty() ? '<span class="text-emerald-700">linked</span>' : '<span class="text-amber-700">none</span>' !!}
                        @endif
                    </td>
                    <td class="px-3 py-1.5 text-right text-xs tabular-nums {{ $e->confidence < 0.8 ? 'text-amber-700' : 'text-slate-400' }}">{{ number_format($e->confidence * 100, 0) }}%</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
@endsection
