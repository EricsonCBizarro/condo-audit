<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('condominiums', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('slug')->unique();
            $table->string('tax_id')->nullable();
            $table->string('city')->nullable();
            // Rule parameters (tolerances, thresholds, category keywords...).
            // Values extracted from documents live in governance_parameters;
            // these are operator-level overrides and defaults.
            $table->jsonb('settings')->default('{}');
            $table->timestamps();
        });

        Schema::create('condominium_user', function (Blueprint $table) {
            $table->id();
            $table->foreignId('condominium_id')->constrained('condominiums')->cascadeOnDelete();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('role');
            $table->timestamps();

            $table->unique(['condominium_id', 'user_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('condominium_user');
        Schema::dropIfExists('condominiums');
    }
};
