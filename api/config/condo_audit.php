<?php

return [
    // Disk holding original documents (bronze layer). Any S3-compatible
    // storage works; local development uses SeaweedFS.
    'documents_disk' => env('DOCUMENTS_DISK', 's3'),

    'pipeline' => [
        'redis_connection' => env('PIPELINE_REDIS_CONNECTION', 'pipeline'),
        'jobs_key' => env('PIPELINE_JOBS_KEY', 'condo-audit:jobs'),
    ],

    // Shared JSON contract between API and worker (used by contract tests).
    'contracts_path' => env('CONTRACTS_PATH', base_path('../contracts')),

    // Demo login created by `php artisan demo:seed` (fictional data only).
    'demo' => [
        'email' => env('DEMO_USER_EMAIL', 'auditor@example.com'),
        'password' => env('DEMO_USER_PASSWORD'),
    ],

    'upload' => [
        'max_kilobytes' => (int) env('UPLOAD_MAX_KB', 20480),
    ],
];
