<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('findings', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignUuid('last_audit_run_id')->nullable()->constrained('pipeline_runs')->nullOnDelete();
            $table->string('rule_code');
            $table->string('category');
            $table->string('severity');
            $table->string('title');
            $table->text('explanation');
            $table->decimal('amount', 14, 2)->nullable();
            // Month (or year) the finding is about, for filtering and evaluation.
            $table->string('period', 7)->nullable();
            $table->jsonb('evidence')->default('[]');
            // Stable hash of what the finding is about (rule + subject).
            // Re-running the audit upserts by it, so review status survives.
            $table->char('fingerprint', 64);
            $table->string('status');
            // False when the latest audit run no longer detects it.
            $table->boolean('is_active')->default(true);
            $table->timestamp('first_detected_at');
            $table->timestamp('last_detected_at');
            $table->timestamps();

            $table->unique(['condominium_id', 'fingerprint']);
            $table->index(['condominium_id', 'status']);
            $table->index(['condominium_id', 'rule_code']);
        });

        Schema::create('finding_events', function (Blueprint $table) {
            $table->id();
            $table->foreignId('finding_id')->constrained()->cascadeOnDelete();
            $table->foreignId('user_id')->nullable()->constrained()->nullOnDelete();
            $table->string('from_status');
            $table->string('to_status');
            $table->text('note')->nullable();
            $table->timestamp('created_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('finding_events');
        Schema::dropIfExists('findings');
    }
};
