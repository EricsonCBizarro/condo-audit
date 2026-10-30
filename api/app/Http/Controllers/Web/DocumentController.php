<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Models\Condominium;
use App\Models\Document;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\View\View;
use Symfony\Component\HttpFoundation\StreamedResponse;

class DocumentController extends Controller
{
    public function index(Condominium $condominium): View
    {
        $this->authorize('view', $condominium);

        return view('documents.index', [
            'condominium' => $condominium,
            'documents' => $condominium->documents()->orderBy('type')->orderBy('reference_period')->orderBy('id')->get(),
        ]);
    }

    /**
     * Side by side: the original page and what the pipeline read from it.
     */
    public function show(Request $request, Condominium $condominium, Document $document): View
    {
        $this->authorize('view', $condominium);
        $pageNumber = max(1, (int) $request->query('page', '1'));

        return view('documents.show', [
            'condominium' => $condominium,
            'document' => $document,
            'pageNumber' => $pageNumber,
            'page' => $document->pages()->with('lines')->where('page_number', $pageNumber)->first(),
            'highlight' => (string) $request->query('highlight', ''),
        ]);
    }

    public function file(Condominium $condominium, Document $document): StreamedResponse
    {
        $this->authorize('view', $condominium);

        return Storage::disk((string) config('condo_audit.documents_disk'))->response(
            $document->storage_key,
            $document->original_filename,
            ['Content-Type' => 'application/pdf'],
            'inline',
        );
    }
}
