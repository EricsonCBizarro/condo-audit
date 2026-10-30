@extends('layouts.app', ['title' => $document->title])

@section('content')
    <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
            <a href="{{ route('documents.index', $condominium) }}" class="text-sm text-slate-500 hover:text-slate-800">← Documents</a>
            <h1 class="text-xl font-semibold">{{ $document->title }}</h1>
        </div>
        <div class="flex items-center gap-2 text-sm">
            @if ($pageNumber > 1)<a class="rounded-md px-2 py-1 ring-1 ring-slate-200 hover:bg-white" href="{{ route('documents.show', [$condominium, $document, 'page' => $pageNumber - 1]) }}">← Prev</a>@endif
            <span class="tabular-nums text-slate-600">Page {{ $pageNumber }} / {{ $document->page_count }}</span>
            @if ($pageNumber < (int) $document->page_count)<a class="rounded-md px-2 py-1 ring-1 ring-slate-200 hover:bg-white" href="{{ route('documents.show', [$condominium, $document, 'page' => $pageNumber + 1]) }}">Next →</a>@endif
        </div>
    </div>

    <div class="mt-4 grid gap-4 lg:grid-cols-2">
        <div class="rounded-lg border border-slate-200 bg-white p-2">
            <canvas class="mx-auto block w-full" data-pdf-src="{{ route('documents.file', [$condominium, $document]) }}" data-pdf-page="{{ $pageNumber }}"></canvas>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white">
            <div class="flex items-center justify-between border-b border-slate-100 px-3 py-2 text-sm">
                <span class="font-medium">What the pipeline read</span>
                @if ($page)
                    <span class="text-xs text-slate-500">{{ $page->text_source === 'ocr' ? 'OCR' : 'native text' }} · page type {{ $page->page_type }} · mean confidence {{ number_format((float) $page->mean_confidence * 100, 0) }}%</span>
                @endif
            </div>
            <ol class="max-h-[70vh] overflow-y-auto p-2 font-mono text-xs leading-relaxed">
                @forelse ($page?->lines ?? [] as $line)
                    @php($hit = $highlight !== '' && str_contains($line->text, $highlight))
                    <li class="flex gap-2 rounded px-1 {{ $hit ? 'bg-amber-100' : '' }} {{ $line->confidence < 0.8 ? 'text-amber-700' : '' }}">
                        <span class="w-10 shrink-0 text-right text-slate-400">{{ number_format($line->confidence * 100, 0) }}%</span>
                        <span class="whitespace-pre-wrap break-words">{{ $line->text }}</span>
                    </li>
                @empty
                    <li class="p-4 text-slate-500">Not processed yet.</li>
                @endforelse
            </ol>
        </div>
    </div>

@endsection
