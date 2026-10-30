<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Models\Condominium;
use Illuminate\Http\Request;
use Illuminate\View\View;

class StatementController extends Controller
{
    public function index(Request $request, Condominium $condominium): View
    {
        $this->authorize('view', $condominium);

        $periods = $condominium->documents()->where('type', 'financial_statement')
            ->orderBy('reference_period')->get(['id', 'title', 'reference_period']);
        $selected = $periods->firstWhere('id', (int) $request->query('document')) ?? $periods->first();

        return view('statements.index', [
            'condominium' => $condominium,
            'periods' => $periods,
            'selected' => $selected,
            'entries' => $selected
                ? $condominium->statementEntries()->where('document_id', $selected->id)->with('receiptLinks')
                    ->orderBy('page_number')->orderBy('line_number')->get()
                : collect(),
        ]);
    }
}
