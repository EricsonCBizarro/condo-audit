<?php

namespace App\Http\Controllers\Api\V1;

use App\Enums\FindingStatus;
use App\Findings\FindingReviewService;
use App\Findings\InvalidFindingTransition;
use App\Http\Controllers\Controller;
use App\Http\Requests\UpdateFindingRequest;
use App\Http\Resources\FindingResource;
use App\Models\Condominium;
use App\Models\Finding;
use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Validation\ValidationException;

class FindingController extends Controller
{
    public function index(Request $request, Condominium $condominium): AnonymousResourceCollection
    {
        $this->authorize('view', $condominium);

        $findings = $condominium->findings()
            ->when(! $request->boolean('include_inactive'), fn ($q) => $q->where('is_active', true))
            ->when($request->query('status'), fn ($q, $v) => $q->where('status', $v))
            ->when($request->query('severity'), fn ($q, $v) => $q->where('severity', $v))
            ->when($request->query('category'), fn ($q, $v) => $q->where('category', $v))
            ->when($request->query('rule'), fn ($q, $v) => $q->where('rule_code', $v))
            ->orderBySeverity()
            ->orderByDesc('amount')
            ->orderBy('id')
            ->paginate(min((int) $request->query('per_page', '25'), 100));

        return FindingResource::collection($findings);
    }

    public function show(Condominium $condominium, Finding $finding): FindingResource
    {
        $this->authorize('view', $condominium);

        return new FindingResource($finding->load('events.user'));
    }

    public function update(UpdateFindingRequest $request, Condominium $condominium, Finding $finding, FindingReviewService $reviews): FindingResource
    {
        /** @var User $user */
        $user = $request->user();

        try {
            $finding = $reviews->transition(
                $finding,
                FindingStatus::from($request->string('status')->toString()),
                $user,
                $request->filled('note') ? $request->string('note')->toString() : null,
            );
        } catch (InvalidFindingTransition $e) {
            throw ValidationException::withMessages(['status' => $e->getMessage()]);
        }

        return new FindingResource($finding->load('events.user'));
    }
}
