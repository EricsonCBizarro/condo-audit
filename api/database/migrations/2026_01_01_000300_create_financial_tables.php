<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Gold layer: bank statement rows extracted from financial statements.
        // Natural key (document, page, line) keeps ids stable across
        // reprocessing, so human decisions linked to them survive.
        Schema::create('statement_entries', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->unsignedInteger('page_number');
            $table->unsignedInteger('line_number');
            $table->string('kind');
            $table->date('entry_date')->nullable();
            $table->string('description');
            $table->decimal('amount', 14, 2)->nullable();
            $table->decimal('balance', 14, 2)->nullable();
            $table->string('category')->nullable();
            $table->string('reconciliation');
            $table->decimal('confidence', 4, 3);
            $table->text('raw_text');
            $table->timestamps();

            $table->unique(['document_id', 'page_number', 'line_number']);
            $table->index(['condominium_id', 'entry_date']);
        });

        Schema::create('receipts', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->unsignedInteger('page_number');
            $table->string('payee')->nullable();
            $table->string('payer_name')->nullable();
            $table->string('payer_tax_id')->nullable();
            $table->decimal('amount', 14, 2)->nullable();
            $table->date('paid_on')->nullable();
            $table->string('description')->nullable();
            $table->decimal('confidence', 4, 3);
            $table->timestamps();

            $table->unique(['document_id', 'page_number']);
        });

        Schema::create('entry_receipt_links', function (Blueprint $table) {
            $table->id();
            $table->foreignId('statement_entry_id')->constrained()->cascadeOnDelete();
            $table->foreignId('receipt_id')->constrained()->cascadeOnDelete();
            $table->decimal('score', 4, 3);
            $table->string('status');
            $table->string('origin');
            $table->timestamps();

            $table->unique(['statement_entry_id', 'receipt_id']);
        });

        Schema::create('budget_items', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('document_id')->constrained()->cascadeOnDelete();
            $table->unsignedSmallInteger('year');
            $table->string('category');
            $table->decimal('monthly_amount', 14, 2);
            $table->unsignedInteger('page_number');
            $table->timestamps();

            $table->unique(['document_id', 'category']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('budget_items');
        Schema::dropIfExists('entry_receipt_links');
        Schema::dropIfExists('receipts');
        Schema::dropIfExists('statement_entries');
    }
};
