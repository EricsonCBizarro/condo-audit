<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('agenda_items', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->date('meeting_date')->nullable();
            $table->unsignedInteger('item_number');
            $table->text('subject');
            $table->unsignedInteger('page_number');
            $table->timestamps();

            $table->unique(['document_id', 'item_number']);
        });

        Schema::create('meeting_decisions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->date('meeting_date')->nullable();
            $table->unsignedInteger('item_number');
            $table->text('subject');
            $table->boolean('approved');
            $table->decimal('approved_amount', 14, 2)->nullable();
            $table->unsignedInteger('page_number');
            $table->timestamps();

            $table->unique(['document_id', 'item_number']);
        });

        Schema::create('bylaw_clauses', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->string('number');
            $table->string('heading')->nullable();
            $table->text('text');
            $table->unsignedInteger('page_number');
            $table->timestamps();

            $table->unique(['document_id', 'number']);
        });

        // Parameters extracted from governing documents (e.g. the spending
        // limit the convention allows without an assembly), with the excerpt
        // they came from so a finding can cite its legal basis.
        Schema::create('governance_parameters', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->string('key');
            $table->jsonb('value');
            $table->text('source_excerpt');
            $table->unsignedInteger('page_number');
            $table->timestamps();

            $table->unique(['document_id', 'key']);
        });

        Schema::create('penalty_notices', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->string('unit');
            $table->string('infraction');
            $table->string('kind');
            $table->decimal('amount', 14, 2)->nullable();
            $table->date('issued_on')->nullable();
            $table->unsignedInteger('page_number');
            $table->timestamps();

            $table->unique(['document_id', 'page_number']);
            $table->index(['condominium_id', 'unit', 'infraction']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('penalty_notices');
        Schema::dropIfExists('governance_parameters');
        Schema::dropIfExists('bylaw_clauses');
        Schema::dropIfExists('meeting_decisions');
        Schema::dropIfExists('agenda_items');
    }
};
