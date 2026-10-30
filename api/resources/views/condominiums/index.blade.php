@extends('layouts.app', ['title' => 'Condominiums'])

@section('content')
    <h1 class="text-xl font-semibold">Condominiums</h1>
    <p class="mt-1 text-sm text-slate-500">Audit status of every condominium you have access to.</p>
    <div class="mt-6 grid gap-4 md:grid-cols-2">
        @forelse ($cards as $card)
            @php($s = $card['summary'])
            <a href="{{ route('condominiums.show', $card['condominium']) }}"
               class="block rounded-lg border border-slate-200 bg-white p-5 transition hover:border-indigo-300 hover:shadow-sm">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <h2 class="font-semibold">{{ $card['condominium']->name }}</h2>
                        <p class="text-sm text-slate-500">{{ $card['condominium']->city }} · {{ $s['documents']['processed'] }}/{{ $s['documents']['total'] }} documents processed</p>
                    </div>
                    @if ($s['findings']['irregularities'] > 0)
                        <span class="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-medium text-orange-800">{{ $s['findings']['irregularities'] }} irregularities</span>
                    @else
                        <span class="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800">no irregularities</span>
                    @endif
                </div>
                <dl class="mt-4 grid grid-cols-3 gap-2 text-sm">
                    <div><dt class="text-slate-500">Open</dt><dd class="font-medium">{{ $s['findings']['open'] }}</dd></div>
                    <div><dt class="text-slate-500">Review items</dt><dd class="font-medium">{{ $s['findings']['data_quality'] }}</dd></div>
                    <div><dt class="text-slate-500">Amount involved</dt><dd class="font-medium">{{ \App\Support\Format::brl($s['findings']['amount_at_stake']) }}</dd></div>
                </dl>
            </a>
        @empty
            <p class="text-sm text-slate-500">No condominiums yet. Run <code>make seed</code>.</p>
        @endforelse
    </div>
@endsection
