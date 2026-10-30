<?php

namespace App\Pipeline;

use App\Enums\JobType;
use DateTimeInterface;

/**
 * One message of the API → pipeline contract (contracts/job.schema.json).
 * Built only by PipelineDispatcher; serialized once, consumed by Python.
 */
final readonly class JobMessage
{
    public const SCHEMA_VERSION = 1;

    /**
     * @param  array<string, mixed>  $payload
     */
    public function __construct(
        public string $jobId,
        public JobType $type,
        public int $condominiumId,
        public string $correlationId,
        public DateTimeInterface $enqueuedAt,
        public array $payload,
        public int $attempt = 0,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return [
            'schema_version' => self::SCHEMA_VERSION,
            'job_id' => $this->jobId,
            'type' => $this->type->value,
            'condominium_id' => $this->condominiumId,
            'correlation_id' => $this->correlationId,
            'enqueued_at' => $this->enqueuedAt->format(DATE_RFC3339_EXTENDED),
            'attempt' => $this->attempt,
            // Empty payload must serialize as an object, not a list.
            'payload' => (object) $this->payload,
        ];
    }

    public function toJson(): string
    {
        return json_encode($this->toArray(), JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
    }
}
