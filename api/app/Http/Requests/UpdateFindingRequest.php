<?php

namespace App\Http\Requests;

use App\Enums\FindingStatus;
use App\Models\Condominium;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateFindingRequest extends FormRequest
{
    public function authorize(): bool
    {
        $condominium = $this->route('condominium');

        return $condominium instanceof Condominium && ($this->user()?->can('review', $condominium) ?? false);
    }

    /** @return array<string, list<mixed>> */
    public function rules(): array
    {
        return [
            'status' => ['required', Rule::enum(FindingStatus::class)],
            'note' => ['nullable', 'string', 'max:2000'],
        ];
    }
}
