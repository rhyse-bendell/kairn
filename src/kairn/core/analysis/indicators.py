from __future__ import annotations
from collections import Counter, defaultdict
from ..export.records import fetch_enriched_events


def compute_indicators_report(db_path, collection_id=None, since_ts=None):
    events = fetch_enriched_events(db_path, collection_id=collection_id)
    if since_ts:
        events = [e for e in events if (e.get("ts") or "") >= since_ts]
    by_actor = Counter((e.get("actor_label") or "unknown") for e in events)
    by_artifact = Counter((e.get("artifact_rel_path") or "unknown") for e in events)
    by_action = Counter((e.get("action") or "unknown") for e in events)
    actor_artifacts = defaultdict(set)
    artifact_actors = defaultdict(set)
    for e in events:
        a = e.get("actor_label") or "unknown"
        ar = e.get("artifact_rel_path") or "unknown"
        actor_artifacts[a].add(ar)
        artifact_actors[ar].add(a)
    total = sum(by_actor.values()) or 1
    return {
        "caution": "Trace-based indicators only; these are not direct measurements of cognition or performance.",
        "participation_contribution_balance": {
            "events_by_actor": dict(by_actor),
            "share_of_events_by_actor": {k: round(v / total, 4) for k, v in by_actor.items()},
            "artifacts_touched_by_actor": {k: len(v) for k, v in actor_artifacts.items()},
        },
        "artifact_activity": {
            "high_activity_artifacts": by_artifact.most_common(10),
            "inactive_artifacts": [k for k, v in by_artifact.items() if v == 1],
            "artifacts_with_no_events": [],
            "artifacts_with_warnings": [e.get("artifact_rel_path") for e in events if (e.get("warning_count_for_artifact_or_unit") or 0) > 0],
        },
        "coordination_signals": {
            "action_mix": dict(by_action),
            "actor_handoff_like_sequences": max(0, len(events) - 1),
            "moved_renamed_events": by_action.get("moved", 0) + by_action.get("renamed", 0),
            "multi_actor_artifacts": [k for k, v in artifact_actors.items() if len(v) > 1],
        },
        "shared_understanding_proxies": {
            "artifacts_with_repeated_revisions": [k for k, v in by_artifact.items() if v > 2],
            "artifacts_touched_by_multiple_actors": [k for k, v in artifact_actors.items() if len(v) > 1],
            "comment_log_content_events": by_action.get("commented", 0) + by_action.get("logged", 0),
            "warning_hotspots": Counter([e.get("artifact_rel_path") for e in events if (e.get("warning_count_for_artifact_or_unit") or 0) > 0]),
        },
        "reentry_candidates": {
            "changes_since_timestamp": len(events),
            "actors_active_since_timestamp": sorted(by_actor.keys()),
            "artifacts_changed_since_timestamp": sorted(by_artifact.keys()),
            "suggested_review_order": [k for k, _ in by_artifact.most_common(10)],
        },
    }
