<?php

namespace App\Findings;

use App\Enums\FindingStatus;
use App\Models\Finding;
use App\Models\User;
use Illuminate\Support\Facades\DB;

final class FindingReviewService
{
    public function transition(Finding $finding, FindingStatus $to, User $reviewer, ?string $note = null): Finding
    {
        return DB::transaction(function () use ($finding, $to, $reviewer, $note) {
            /** @var Finding $locked */
            $locked = Finding::query()->lockForUpdate()->findOrFail($finding->id);
            $from = $locked->status;

            if (! $from->canTransitionTo($to)) {
                throw InvalidFindingTransition::between($from, $to);
            }

            $locked->update(['status' => $to]);
            $locked->events()->create([
                'user_id' => $reviewer->id,
                'from_status' => $from,
                'to_status' => $to,
                'note' => $note,
                'created_at' => now(),
            ]);

            return $locked->refresh();
        });
    }
}
