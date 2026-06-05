"""
Run an exact-search scale benchmark for face_api.

The script can benchmark an existing SQLite face database or seed deterministic
synthetic embeddings until the requested target count is reached. It does not
start FastAPI and does not call InsightFace, so it is safe for offline capacity
planning.
"""
import argparse
import json
import platform
import random
import statistics
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from storage import FaceDB  # noqa: E402


def percentile(values, percent):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percent / 100))
    return float(ordered[index])


def make_embedding(seed):
    rng = np.random.default_rng(seed)
    vector = rng.normal(size=512).astype(np.float32)
    vector = vector / (np.linalg.norm(vector) + 1e-8)
    return vector.tolist()


def seed_synthetic_faces(db, target_count, batch_label):
    existing = db.count()
    added = 0
    for idx in range(existing, target_count):
        db.add(
            username=f"synthetic_{idx:06d}",
            user_id=idx,
            embedding=make_embedding(idx),
            metadata={"source": "benchmark-scale", "batch": batch_label},
        )
        added += 1
        if added % 1000 == 0:
            print(f"seeded {added} synthetic faces, total target {target_count}")
    return added


def run_search_samples(db, sample_count, top_k, threshold, seed):
    rng = random.Random(seed)
    elapsed_values = []
    failure_reasons = {}

    for sample_index in range(sample_count):
        query_seed = rng.randint(0, max(sample_count * 100, 1000))
        query = make_embedding(query_seed)
        started = time.perf_counter()
        try:
            db.search(query, top_k=top_k, threshold=threshold)
        except Exception as exc:  # pragma: no cover - defensive CLI path
            reason = exc.__class__.__name__
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            continue
        elapsed_values.append((time.perf_counter() - started) * 1000)
        if (sample_index + 1) % 50 == 0:
            print(f"completed {sample_index + 1}/{sample_count} search samples")

    return elapsed_values, failure_reasons


def build_report(args, db, added_count, elapsed_values, failure_reasons):
    avg_ms = statistics.mean(elapsed_values) if elapsed_values else 0.0
    p95_ms = percentile(elapsed_values, 95)
    target_met = p95_ms <= args.target_latency_ms and not failure_reasons
    return {
        "version": "1.0",
        "generated_at_epoch": round(time.time(), 3),
        "target_record_count": args.target_count,
        "target_latency_ms": args.target_latency_ms,
        "record_count": db.count(),
        "seeded_synthetic_count": added_count,
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor(),
            "db_path": str(Path(args.db_path).resolve()),
        },
        "search": {
            "samples": args.sample_count,
            "top_k": args.top_k,
            "threshold": args.threshold,
            "avg_ms": round(avg_ms, 2),
            "p95_ms": round(p95_ms, 2),
            "min_ms": round(min(elapsed_values), 2) if elapsed_values else 0.0,
            "max_ms": round(max(elapsed_values), 2) if elapsed_values else 0.0,
            "failure_count": sum(failure_reasons.values()),
            "failure_reasons": failure_reasons,
        },
        "index_decision": {
            "current_mode": "exact",
            "should_evaluate_index": not target_met,
            "reason": (
                "精确搜索达到目标，继续保留默认 exact 模式"
                if target_met
                else "P95 或失败率未达目标，进入 index 方案评估"
            ),
            "fallback_required": True,
        },
        "conclusion": "pass" if target_met else "needs_index_evaluation",
    }


def main():
    parser = argparse.ArgumentParser(description="face_api 5万人脸规模 benchmark")
    parser.add_argument("--db-path", default="faces.db", help="SQLite database path")
    parser.add_argument("--target-count", type=int, default=50000)
    parser.add_argument("--target-latency-ms", type=float, default=1000.0)
    parser.add_argument("--sample-count", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=20260605)
    parser.add_argument("--seed-synthetic", action="store_true", help="seed synthetic embeddings up to target count")
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="allow --seed-synthetic to write into --db-path; default uses a temporary benchmark database",
    )
    parser.add_argument("--batch-label", default="scale-v1.6")
    parser.add_argument("--output", default="reports/performance/benchmark-scale.json")
    args = parser.parse_args()

    temp_dir = None
    if args.seed_synthetic and not args.write_db:
        temp_dir = tempfile.TemporaryDirectory()
        args.db_path = str(Path(temp_dir.name) / "benchmark-scale.db")

    db = FaceDB(args.db_path)
    added_count = 0
    try:
        if args.seed_synthetic:
            added_count = seed_synthetic_faces(db, args.target_count, args.batch_label)

        db.invalidate_search_cache()
        elapsed_values, failure_reasons = run_search_samples(
            db,
            sample_count=args.sample_count,
            top_k=args.top_k,
            threshold=args.threshold,
            seed=args.seed,
        )
        report = build_report(args, db, added_count, elapsed_values, failure_reasons)
        report["runtime"]["temporary_db"] = bool(temp_dir)

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        db.close()
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    main()
