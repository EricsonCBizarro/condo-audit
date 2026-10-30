<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Models\Condominium;
use App\Models\User;
use App\Reports\AuditSummary;
use Illuminate\Http\Request;
use Illuminate\View\View;

class DashboardController extends Controller
{
    public function index(Request $request, AuditSummary $summary): View
    {
        /** @var User $user */
        $user = $request->user();
        $condominiums = $user->condominiums()->orderBy('name')->get();

        return view('condominiums.index', [
            'cards' => $condominiums->map(fn (Condominium $c) => ['condominium' => $c, 'summary' => $summary->for($c)]),
        ]);
    }

    public function show(Request $request, Condominium $condominium, AuditSummary $summary): View
    {
        $this->authorize('view', $condominium);

        $findings = $condominium->findings()
            ->where('is_active', true)
            ->when($request->query('status'), fn ($q, $v) => $q->where('status', $v))
            ->when($request->query('category'), fn ($q, $v) => $q->where('category', $v))
            ->orderBySeverity()
            ->orderByDesc('amount')
            ->get();

        return view('condominiums.show', [
            'condominium' => $condominium,
            'summary' => $summary->for($condominium),
            'findings' => $findings,
            'ocrPages' => $condominium->documents()->join('document_pages', 'document_pages.document_id', '=', 'documents.id')
                ->where('document_pages.text_source', 'ocr')->count(),
        ]);
    }
}
