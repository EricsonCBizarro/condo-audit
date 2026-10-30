<?php

namespace App\Http\Middleware;

use App\Support\CorrelationId;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * Accepts a caller-supplied correlation id (if well-formed) or creates one.
 * It ends up in every log line (Laravel Context), in the queued job and in
 * the response header.
 */
class AssignCorrelationId
{
    public function handle(Request $request, Closure $next): Response
    {
        $incoming = (string) $request->headers->get(CorrelationId::HEADER, '');
        CorrelationId::set(CorrelationId::isValid($incoming) ? $incoming : CorrelationId::generate());

        $response = $next($request);
        $response->headers->set(CorrelationId::HEADER, CorrelationId::current());

        return $response;
    }
}
