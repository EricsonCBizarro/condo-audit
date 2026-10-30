@extends('layouts.app', ['title' => 'Documents'])

@section('content')
    <h1 class="text-xl font-semibold">Documents</h1>
    <p class="mt-1 text-sm text-slate-500">Originals are immutable (SHA-256); everything else is derived from them.</p>
    <div class="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table class="w-full text-sm">
            <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr><th class="px-3 py-2">Document</th><th class="px-3 py-2">Type</th><th class="px-3 py-2">Period</th><th class="px-3 py-2 text-right">Pages</th><th class="px-3 py-2">Read by</th><th class="px-3 py-2">Status</th><th class="px-3 py-2">SHA-256</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
            @foreach ($documents as $document)
                <tr class="hover:bg-slate-50">
                    <td class="px-3 py-2"><a class="text-indigo-700 hover:underline" href="{{ route('documents.show', [$condominium, $document]) }}">{{ $document->title }}</a></td>
                    <td class="px-3 py-2 text-slate-600">{{ \App\Support\Format::label($document->type->value) }}</td>
                    <td class="px-3 py-2 tabular-nums">{{ $document->reference_period?->format('m/Y') ?? '—' }}</td>
                    <td class="px-3 py-2 text-right tabular-nums">{{ $document->page_count }}</td>
                    <td class="px-3 py-2">
                        @if ($document->text_source === 'ocr')<span class="rounded bg-violet-50 px-1.5 py-0.5 text-xs text-violet-700 ring-1 ring-violet-200">OCR</span>
                        @else<span class="text-xs text-slate-500">{{ $document->text_source ?? '—' }}</span>@endif
                    </td>
                    <td class="px-3 py-2 text-slate-600">{{ $document->status->value }}</td>
                    <td class="px-3 py-2 font-mono text-xs text-slate-400">{{ substr($document->sha256, 0, 12) }}…</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
@endsection
