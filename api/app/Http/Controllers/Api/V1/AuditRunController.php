<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\PipelineRunResource;
use App\Models\Condominium;
use App\Models\PipelineRun;
use App\Pipeline\PipelineDispatcher;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AuditRunController extends Controller
{
    public function store(Request $request, Condominium $condominium, PipelineDispatcher $dispatcher): JsonResponse
    {
        $this->authorize('runAudit', $condominium);

        $validated = $request->validate([
            'rules' => ['nullable', 'array'],
            'rules.*' => ['string', 'regex:/^[A-Z_]+$/'],
        ]);

        /** @var list<string> $rules */
        $rules = array_values($validated['rules'] ?? []);

        return (new PipelineRunResource($dispatcher->runAudit($condominium, $rules)))
            ->response()
            ->setStatusCode(202);
    }

    public function show(Condominium $condominium, PipelineRun $pipelineRun): PipelineRunResource
    {
        $this->authorize('view', $condominium);

        return new PipelineRunResource($pipelineRun);
    }
}
