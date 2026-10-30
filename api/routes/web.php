<?php

use App\Http\Controllers\Web\DashboardController;
use App\Http\Controllers\Web\DocumentController;
use App\Http\Controllers\Web\FindingController;
use App\Http\Controllers\Web\LoginController;
use App\Http\Controllers\Web\StatementController;
use Illuminate\Support\Facades\Route;

Route::get('login', [LoginController::class, 'show'])->middleware('guest')->name('login');
Route::post('login', [LoginController::class, 'store'])->middleware(['guest', 'throttle:10,1']);
Route::post('logout', [LoginController::class, 'destroy'])->middleware('auth')->name('logout');

Route::middleware('auth')->group(function () {
    Route::redirect('/', '/condominiums');
    Route::get('condominiums', [DashboardController::class, 'index'])->name('condominiums.index');

    Route::prefix('condominiums/{condominium}')->scopeBindings()->group(function () {
        Route::get('/', [DashboardController::class, 'show'])->name('condominiums.show');
        Route::get('findings/{finding}', [FindingController::class, 'show'])->name('findings.show');
        Route::post('findings/{finding}/review', [FindingController::class, 'review'])->name('findings.review');
        Route::get('documents', [DocumentController::class, 'index'])->name('documents.index');
        Route::get('documents/{document}', [DocumentController::class, 'show'])->name('documents.show');
        Route::get('documents/{document}/file', [DocumentController::class, 'file'])->name('documents.file');
        Route::get('statements', [StatementController::class, 'index'])->name('statements.index');
    });
});
