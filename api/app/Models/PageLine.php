<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class PageLine extends Model
{
    public $timestamps = false;

    protected $guarded = [];

    protected function casts(): array
    {
        return ['bbox' => 'array', 'confidence' => 'float'];
    }
}
