<?php

namespace App\Reports;

use App\Enums\DocumentStatus;
use App\Enums\FindingCategory;
use App\Enums\FindingStatus;
use App\Models\Condominium;
use Illuminate\Support\Facades\DB;

/**
 * Aggregates for the dashboard and the report endpoint. Only active
 * findings (still detected by the latest audit run) are counted.
 */
final class AuditSummary
{
    /**
     * @return array{
     *     documents: array{total: int, processed: int, failed: int, pending: int},
     *     findings: array{total: int, open: int, confirmed: int, dismissed: int, irregularities: int, data_quality: int, amount_at_stake: string},
     *     by_severity: array<string, int>,
     *     by_rule: array<string, int>,
     *     last_audit_at: ?string,
     * }
     */
    public function for(Condominium $condominium): array
    {
        $documents = $condominium->documents()
            ->select('status', DB::raw('count(*) as total'))
            ->groupBy('status')
            ->pluck('total', 'status');

        $findings = $condominium->findings()->where('is_active', true);

        $byStatus = (clone $findings)->select('status', DB::raw('count(*) as total'))->groupBy('status')->pluck('total', 'status');
        $byCategory = (clone $findings)->select('category', DB::raw('count(*) as total'))->groupBy('category')->pluck('total', 'category');
        $bySeverity = (clone $findings)->select('severity', DB::raw('count(*) as total'))->groupBy('severity')->pluck('total', 'severity');
        $byRule = (clone $findings)->select('rule_code', DB::raw('count(*) as total'))->groupBy('rule_code')->orderByDesc('total')->pluck('total', 'rule_code');
        $amount = (clone $findings)
            ->where('category', FindingCategory::Irregularity)
            ->where('status', '!=', FindingStatus::Dismissed)
            ->sum('amount');

        $lastAudit = $condominium->findings()->max('last_detected_at');

        return [
            'documents' => [
                'total' => (int) $documents->sum(),
                'processed' => (int) ($documents[DocumentStatus::Processed->value] ?? 0),
                'failed' => (int) ($documents[DocumentStatus::Failed->value] ?? 0),
                'pending' => (int) (($documents[DocumentStatus::Pending->value] ?? 0) + ($documents[DocumentStatus::Processing->value] ?? 0)),
            ],
            'findings' => [
                'total' => (int) $byStatus->sum(),
                'open' => (int) ($byStatus[FindingStatus::Open->value] ?? 0),
                'confirmed' => (int) ($byStatus[FindingStatus::Confirmed->value] ?? 0),
                'dismissed' => (int) ($byStatus[FindingStatus::Dismissed->value] ?? 0),
                'irregularities' => (int) ($byCategory[FindingCategory::Irregularity->value] ?? 0),
                'data_quality' => (int) ($byCategory[FindingCategory::DataQuality->value] ?? 0),
                'amount_at_stake' => number_format((float) $amount, 2, '.', ''),
            ],
            'by_severity' => array_map('intval', $bySeverity->all()),
            'by_rule' => array_map('intval', $byRule->all()),
            'last_audit_at' => is_string($lastAudit) ? $lastAudit : null,
        ];
    }
}
