<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // One row per queued job. The API inserts it as `queued` when it
        // publishes the message; the Python worker owns every later
        // transition (running, succeeded, failed, dead).
        Schema::create('pipeline_runs', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->nullable()->constrained()->nullOnDelete();
            $table->string('job_type');
            $table->string('status');
            $table->unsignedInteger('attempts')->default(0);
            $table->string('correlation_id');
            $table->timestamp('queued_at');
            $table->timestamp('started_at')->nullable();
            $table->timestamp('finished_at')->nullable();
            $table->text('error')->nullable();
            $table->jsonb('stats')->default('{}');
            $table->timestamps();

            $table->index(['condominium_id', 'status']);
            $table->index('correlation_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('pipeline_runs');
    }
};
