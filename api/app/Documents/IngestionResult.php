<?php

namespace App\Documents;

use App\Models\Document;
use App\Models\PipelineRun;

final readonly class IngestionResult
{
    public function __construct(
        public Document $document,
        public bool $duplicate,
        public ?PipelineRun $run,
    ) {}
}
