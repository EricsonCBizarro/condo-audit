<?php

namespace App\Pipeline;

interface JobQueue
{
    public function push(JobMessage $message): void;
}
