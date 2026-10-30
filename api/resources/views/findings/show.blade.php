@extends('layouts.app', ['title' => $finding->title])

@section('content')
    <a href="{{ route('condominiums.show', $condominium) }}" class="text-sm text-slate-500 hover:text-slate-800">← All findings</a>
    <div class="mt-3 grid gap-6 lg:grid-cols-3">
        <section class="lg:col-span-2">
            <div class="flex flex-wrap items-center gap-2">
                <x-severity :value="$finding->severity->value"/>
                <x-status :value="$finding->status->value"/>
                <span class="font-mono text-xs text-slate-500">{{ $finding->rule_code }}</span>
                @if ($finding->period)<span class="text-xs text-slate-500">· {{ $finding->period }}</span>@endif
            </div>
            <h1 class="mt-2 text-xl font-semibold">{{ $finding->title }}</h1>
            <p class="mt-3 leading-relaxed text-slate-700">{{ $finding->explanation }}</p>
            @if ($finding->amount !== null)
                <p class="mt-3 text-sm text-slate-500">Amount involved: <span class="font-medium text-slate-800">{{ \App\Support\Format::brl($finding->amount) }}</span></p>
            @endif

            <h2 class="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">Evidence</h2>
            <ul class="mt-2 space-y-2">
                @foreach ($finding->evidence as $evidence)
                    @php($doc = $documents[$evidence['document_id'] ?? 0] ?? null)
                    <li class="rounded-lg border border-slate-200 bg-white p-3">
                        <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
                            <span><span class="font-medium">{{ ucfirst($evidence['label'] ?? 'source') }}</span>
                                <span class="text-slate-500">— {{ $doc?->title ?? 'document '.($evidence['document_id'] ?? '?') }}, page {{ $evidence['page'] ?? '?' }}</span></span>
                            @if ($doc)
                                <a class="text-indigo-700 hover:underline" href="{{ route('documents.show', [$condominium, $doc, 'page' => $evidence['page'] ?? 1, 'highlight' => \Illuminate\Support\Str::limit($evidence['excerpt'] ?? '', 40, '')]) }}">Open page →</a>
                            @endif
                        </div>
                        <code class="mt-2 block whitespace-pre-wrap break-words rounded bg-slate-50 px-2 py-1.5 text-xs text-slate-700">{{ $evidence['excerpt'] ?? '' }}</code>
                    </li>
                @endforeach
            </ul>
        </section>

        <aside class="space-y-4">
            @can('review', $condominium)
                <form method="POST" action="{{ route('findings.review', [$condominium, $finding]) }}" class="rounded-lg border border-slate-200 bg-white p-4">
                    @csrf
                    <h2 class="text-sm font-semibold">Review</h2>
                    <textarea name="note" rows="3" placeholder="Note (optional)" class="mt-2 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"></textarea>
                    <div class="mt-2 flex flex-wrap gap-2">
                        @if ($finding->status->value === 'open')
                            <button name="status" value="confirmed" class="rounded-md bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-700">Confirm</button>
                            <button name="status" value="dismissed" class="rounded-md bg-white px-3 py-1.5 text-sm ring-1 ring-slate-300 hover:bg-slate-50">Dismiss</button>
                        @else
                            <button name="status" value="open" class="rounded-md bg-white px-3 py-1.5 text-sm ring-1 ring-slate-300 hover:bg-slate-50">Reopen</button>
                        @endif
                    </div>
                </form>
            @endcan
            <div class="rounded-lg border border-slate-200 bg-white p-4">
                <h2 class="text-sm font-semibold">History</h2>
                <ol class="mt-2 space-y-2 text-sm">
                    @foreach ($finding->events as $event)
                        <li><span class="text-slate-500">{{ $event->created_at->format('d/m/Y H:i') }}</span> · {{ $event->user?->name ?? 'system' }}:
                            {{ $event->from_status->value }} → <strong>{{ $event->to_status->value }}</strong>
                            @if ($event->note)<div class="text-slate-600">“{{ $event->note }}”</div>@endif
                        </li>
                    @endforeach
                    <li><span class="text-slate-500">{{ $finding->first_detected_at->format('d/m/Y H:i') }}</span> · detected by the audit</li>
                </ol>
            </div>
        </aside>
    </div>
@endsection
