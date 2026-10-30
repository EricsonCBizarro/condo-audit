<?php

namespace App\Http\Controllers\Web;

use App\Enums\FindingStatus;
use App\Findings\FindingReviewService;
use App\Findings\InvalidFindingTransition;
use App\Http\Controllers\Controller;
use App\Models\Condominium;
use App\Models\Finding;
use App\Models\User;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Illuminate\View\View;

class FindingController extends Controller
{
    public function show(Condominium $condominium, Finding $finding): View
    {
        $this->authorize('view', $condominium);

        $documentIds = collect($finding->evidence)->pluck('document_id')->filter()->unique();

        return view('findings.show', [
            'condominium' => $condominium,
            'finding' => $finding->load('events.user'),
            'documents' => $condominium->documents()->whereIn('id', $documentIds)->get()->keyBy('id'),
        ]);
    }

    public function review(Request $request, Condominium $condominium, Finding $finding, FindingReviewService $reviews): RedirectResponse
    {
        $this->authorize('review', $condominium);
        $data = $request->validate([
            'status' => ['required', Rule::enum(FindingStatus::class)],
            'note' => ['nullable', 'string', 'max:2000'],
        ]);

        /** @var User $user */
        $user = $request->user();
        try {
            $reviews->transition($finding, FindingStatus::from($data['status']), $user, $data['note'] ?? null);
        } catch (InvalidFindingTransition $e) {
            return back()->withErrors(['status' => $e->getMessage()]);
        }

        return redirect()->route('findings.show', [$condominium, $finding])->with('status', 'Review saved.');
    }
}
