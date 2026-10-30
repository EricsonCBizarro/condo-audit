<?php

namespace App\Http\Requests;

use App\Enums\DocumentType;
use App\Models\Condominium;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreDocumentRequest extends FormRequest
{
    public function authorize(): bool
    {
        $condominium = $this->route('condominium');

        return $condominium instanceof Condominium && ($this->user()?->can('upload', $condominium) ?? false);
    }

    /** @return array<string, list<mixed>> */
    public function rules(): array
    {
        return [
            'file' => ['required', 'file', 'mimetypes:application/pdf', 'max:'.config('condo_audit.upload.max_kilobytes')],
            'type' => ['required', Rule::enum(DocumentType::class)],
            'title' => ['nullable', 'string', 'max:255'],
            'reference_period' => ['nullable', 'date_format:Y-m'],
        ];
    }
}
