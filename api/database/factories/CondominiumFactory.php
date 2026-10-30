<?php

namespace Database\Factories;

use App\Models\Condominium;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/** @extends Factory<Condominium> */
class CondominiumFactory extends Factory
{
    /** @return array<string, mixed> */
    public function definition(): array
    {
        $name = 'Residencial '.$this->faker->unique()->lastName();

        return [
            'name' => $name,
            'slug' => Str::slug($name).'-'.$this->faker->unique()->numberBetween(1, 99999),
            'city' => 'Cidade Exemplo',
            'settings' => [],
        ];
    }
}
