<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\CondominiumResource;
use App\Models\Condominium;
use App\Reports\AuditSummary;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class CondominiumController extends Controller
{
    public function index(Request $request): AnonymousResourceCollection
    {
        return CondominiumResource::collection($request->user()?->condominiums()->orderBy('name')->get() ?? collect());
    }

    public function show(Condominium $condominium): CondominiumResource
    {
        $this->authorize('view', $condominium);

        return new CondominiumResource($condominium);
    }

    public function summary(Condominium $condominium, AuditSummary $summary): JsonResponse
    {
        $this->authorize('view', $condominium);

        return response()->json(['data' => $summary->for($condominium)]);
    }
}
