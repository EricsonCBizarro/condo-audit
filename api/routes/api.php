<?php

use App\Http\Controllers\Api\V1\AuditRunController;
use App\Http\Controllers\Api\V1\AuthTokenController;
use App\Http\Controllers\Api\V1\CondominiumController;
use App\Http\Controllers\Api\V1\DocumentController;
use App\Http\Controllers\Api\V1\FindingController;
use App\Http\Controllers\Api\V1\HealthController;
use App\Http\Controllers\Api\V1\StatementEntryController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->name('api.v1.')->group(function () {
    Route::get('health', HealthController::class)->name('health');
    Route::post('auth/token', [AuthTokenController::class, 'store'])->middleware('throttle:10,1')->name('auth.token');

    Route::middleware('auth:sanctum')->group(function () {
        Route::get('condominiums', [CondominiumController::class, 'index'])->name('condominiums.index');

        Route::prefix('condominiums/{condominium}')->scopeBindings()->group(function () {
            Route::get('/', [CondominiumController::class, 'show'])->name('condominiums.show');
            Route::get('summary', [CondominiumController::class, 'summary'])->name('condominiums.summary');

            Route::get('documents', [DocumentController::class, 'index'])->name('documents.index');
            Route::post('documents', [DocumentController::class, 'store'])->name('documents.store');
            Route::get('documents/{document}', [DocumentController::class, 'show'])->name('documents.show');
            Route::get('documents/{document}/file', [DocumentController::class, 'file'])->name('documents.file');

            Route::get('statement-entries', [StatementEntryController::class, 'index'])->name('statement-entries.index');

            Route::post('audit-runs', [AuditRunController::class, 'store'])->name('audit-runs.store');
            Route::get('pipeline-runs/{pipelineRun}', [AuditRunController::class, 'show'])->name('pipeline-runs.show');

            Route::get('findings', [FindingController::class, 'index'])->name('findings.index');
            Route::get('findings/{finding}', [FindingController::class, 'show'])->name('findings.show');
            Route::patch('findings/{finding}', [FindingController::class, 'update'])->name('findings.update');
        });
    });
});
