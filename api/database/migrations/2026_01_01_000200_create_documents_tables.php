<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Bronze layer: one row per original file. Never edited after
        // ingestion except for processing status.
        Schema::create('documents', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->string('type');
            $table->string('title');
            $table->date('reference_period')->nullable();
            $table->string('original_filename');
            $table->string('storage_key');
            $table->string('mime_type');
            $table->unsignedBigInteger('size_bytes');
            $table->char('sha256', 64);
            $table->unsignedInteger('page_count')->nullable();
            $table->string('status');
            $table->string('text_source')->nullable();
            $table->timestamp('ingested_at');
            $table->timestamp('processed_at')->nullable();
            $table->jsonb('metadata')->default('{}');
            $table->timestamps();

            $table->unique(['condominium_id', 'sha256']);
            $table->index(['condominium_id', 'type']);
            $table->index('status');
        });

        // Silver layer: what was read from each page, with provenance.
        Schema::create('document_pages', function (Blueprint $table) {
            $table->id();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->unsignedInteger('page_number');
            $table->string('page_type');
            $table->string('text_source');
            $table->text('text');
            $table->decimal('mean_confidence', 4, 3)->nullable();
            $table->timestamps();

            $table->unique(['document_id', 'page_number']);
        });

        Schema::create('page_lines', function (Blueprint $table) {
            $table->id();
            $table->foreignId('document_page_id')->constrained()->cascadeOnDelete();
            $table->unsignedInteger('line_number');
            $table->text('text');
            $table->jsonb('bbox');
            $table->decimal('confidence', 4, 3);

            $table->unique(['document_page_id', 'line_number']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('page_lines');
        Schema::dropIfExists('document_pages');
        Schema::dropIfExists('documents');
    }
};
