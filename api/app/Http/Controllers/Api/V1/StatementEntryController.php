<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\StatementEntryResource;
use App\Models\Condominium;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class StatementEntryController extends Controller
{
    public function index(Request $request, Condominium $condominium): AnonymousResourceCollection
    {
        $this->authorize('view', $condominium);

        $validated = $request->validate([
            'from' => ['nullable', 'date'],
            'to' => ['nullable', 'date'],
            'reconciliation' => ['nullable', 'string'],
            'document_id' => ['nullable', 'integer'],
            'per_page' => ['nullable', 'integer', 'min:1', 'max:200'],
        ]);

        $entries = $condominium->statementEntries()
            ->when($validated['from'] ?? null, fn ($q, $from) => $q->where('entry_date', '>=', $from))
            ->when($validated['to'] ?? null, fn ($q, $to) => $q->where('entry_date', '<=', $to))
            ->when($validated['reconciliation'] ?? null, fn ($q, $r) => $q->where('reconciliation', $r))
            ->when($validated['document_id'] ?? null, fn ($q, $d) => $q->where('document_id', $d))
            ->orderBy('entry_date')
            ->orderBy('document_id')
            ->orderBy('page_number')
            ->orderBy('line_number')
            ->paginate((int) ($validated['per_page'] ?? 50));

        return StatementEntryResource::collection($entries);
    }
}
