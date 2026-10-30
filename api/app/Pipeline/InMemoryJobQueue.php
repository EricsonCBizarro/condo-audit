<?php

namespace App\Pipeline;

/** Test double: keeps published messages in memory. */
final class InMemoryJobQueue implements JobQueue
{
    /** @var list<JobMessage> */
    public array $messages = [];

    public function push(JobMessage $message): void
    {
        $this->messages[] = $message;
    }
}
