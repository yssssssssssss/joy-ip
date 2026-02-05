#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单压测脚本（用于对比优化前后的吞吐/超时率）

示例：
  python test/perf/load_test.py --base-url http://127.0.0.1:28888 --concurrency 5 --requests 10
  python test/perf/load_test.py --base-url http://127.0.0.1:28888 --concurrency 20 --requests 40 --skip-analyze

说明：
- 默认走：analyze(async) → start_generate(携带analysis) → polling(status)
- --skip-analyze：直接 start_generate（由后端自行分析）
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import statistics
import time
from typing import Any, Dict, List, Tuple

import requests


def _now_ms() -> int:
    return int(time.time() * 1000)

def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    p = max(0.0, min(1.0, float(p)))
    idx = int(round((len(vals) - 1) * p))
    idx = max(0, min(len(vals) - 1, idx))
    return vals[idx]


def _get_stage_ms(stage_timings: Any, stage: str) -> int:
    try:
        timings = stage_timings if isinstance(stage_timings, dict) else {}
        entry = timings.get(stage) or {}
        if not isinstance(entry, dict):
            return 0
        if isinstance(entry.get("ms"), (int, float)):
            return int(entry["ms"])
        start = entry.get("start")
        end = entry.get("end")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start:
            return int((end - start) * 1000)
    except Exception:
        pass
    return 0


def _fetch_queue_stats(session: requests.Session, base_url: str) -> Dict[str, Any]:
    try:
        r = session.get(f"{base_url}/api/queue/stats", timeout=10)
        data = r.json()
        if isinstance(data, dict) and data.get("success") and isinstance(data.get("stats"), dict):
            return data["stats"]
    except Exception:
        pass
    return {}


def _poll_job(session: requests.Session, base_url: str, job_id: str, timeout_s: int = 600) -> Dict[str, Any]:
    start = time.time()
    while True:
        if time.time() - start > timeout_s:
            return {"success": False, "status": "timeout", "job_id": job_id}

        r = session.get(f"{base_url}/api/job/{job_id}/status", timeout=30)
        data = r.json()
        if not data.get("success"):
            time.sleep(1.0)
            continue
        job = data.get("job") or {}
        status = job.get("status")
        if status in ("succeeded", "failed", "cancelled"):
            return {"success": True, "status": status, "job": job}
        time.sleep(1.0)


def _one_request(
    base_url: str,
    requirement: str,
    skip_analyze: bool,
    mode: str,
    perspective: str,
) -> Dict[str, Any]:
    session = requests.Session()
    t0 = time.time()

    analysis = None
    if not skip_analyze:
        try:
            a = session.post(
                f"{base_url}/api/analyze",
                json={"requirement": requirement, "mode": mode, "perspective": perspective, "async": True},
                timeout=30,
            ).json()
        except Exception as e:
            return {"ok": False, "duration_s": time.time() - t0, "status": "analyze_http_error", "error": str(e)}
        if not a.get("success") or not a.get("job_id"):
            return {
                "ok": False,
                "duration_s": time.time() - t0,
                "status": "analyze_start_failed",
                "code": a.get("code"),
                "error": a.get("error") or a.get("reason"),
            }
        analyze_job_id = a["job_id"]
        analyze_res = _poll_job(session, base_url, analyze_job_id, timeout_s=180)
        if analyze_res.get("status") != "succeeded":
            return {
                "ok": False,
                "duration_s": time.time() - t0,
                "status": f"analyze_{analyze_res.get('status')}",
                "analyze_job": analyze_res.get("job"),
            }
        analysis = (analyze_res.get("job") or {}).get("analysis")
        if not isinstance(analysis, dict):
            return {"ok": False, "duration_s": time.time() - t0, "status": "analyze_no_analysis"}

    payload: Dict[str, Any] = {"requirement": requirement, "mode": mode}
    if mode == "2D":
        payload["perspective"] = perspective
    if analysis:
        payload["analysis"] = analysis

    try:
        s = session.post(f"{base_url}/api/start_generate", json=payload, timeout=30).json()
    except Exception as e:
        return {"ok": False, "duration_s": time.time() - t0, "status": "start_generate_http_error", "error": str(e)}
    if not s.get("success") or not s.get("job_id"):
        code = s.get("code") or "START_FAILED"
        return {
            "ok": False,
            "duration_s": time.time() - t0,
            "status": f"start_generate_{code}",
            "code": code,
            "error": s.get("error"),
        }

    job_id = s["job_id"]
    gen_res = _poll_job(session, base_url, job_id, timeout_s=600)
    status = gen_res.get("status")
    job = gen_res.get("job") or {}
    timings = job.get("stage_timings") or {}
    ok = status == "succeeded"
    return {
        "ok": ok,
        "duration_s": time.time() - t0,
        "status": str(status),
        "job_id": job_id,
        "gen_queued_ms": _get_stage_ms(timings, "queued"),
        "gen_analyze_ms": _get_stage_ms(timings, "analyze"),
        "gen_match_ms": _get_stage_ms(timings, "match"),
        "gen_compose_ms": _get_stage_ms(timings, "compose"),
        "gen_decorate_ms": _get_stage_ms(timings, "decorate"),
        "gen_gate_ms": _get_stage_ms(timings, "gate"),
        "gen_validate_ms": _get_stage_ms(timings, "validate"),
        "gen_processing_s": float((job.get("details") or {}).get("processing_time") or 0.0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:28888")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--skip-analyze", action="store_true")
    parser.add_argument("--mode", default="3D", choices=["2D", "3D"])
    parser.add_argument("--perspective", default="正视角", choices=["正视角", "仰视角"])
    parser.add_argument("--requirement", default="一个开心站立的角色，穿红色上衣，戴帽子，手拿气球")
    args = parser.parse_args()

    print("==== load_test ====")
    print(f"base_url={args.base_url}")
    print(f"concurrency={args.concurrency} requests={args.requests} skip_analyze={args.skip_analyze}")
    print(f"mode={args.mode} perspective={args.perspective}")
    print("===================")

    t0_ms = _now_ms()
    results: List[Dict[str, Any]] = []

    warm = requests.Session()
    before_stats = _fetch_queue_stats(warm, args.base_url)
    if before_stats:
        print("queue_stats_before=", before_stats)

    with futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [
            ex.submit(_one_request, args.base_url, args.requirement, args.skip_analyze, args.mode, args.perspective)
            for _ in range(args.requests)
        ]
        for f in futures.as_completed(futs):
            results.append(f.result())

    total_s = (_now_ms() - t0_ms) / 1000.0
    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count
    durations = [float(r.get("duration_s") or 0.0) for r in results if r.get("duration_s") is not None]
    queued_ms = [int(r.get("gen_queued_ms") or 0) for r in results if int(r.get("gen_queued_ms") or 0) > 0]
    processing_s = [float(r.get("gen_processing_s") or 0.0) for r in results if float(r.get("gen_processing_s") or 0.0) > 0.0]

    print("\n==== summary ====")
    print(f"total_requests={len(results)} ok={ok_count} fail={fail_count}")
    print(f"total_time_s={total_s:.2f} throughput_rps={(len(results) / max(1e-6, total_s)):.2f}")
    if durations:
        print(f"avg_s={statistics.mean(durations):.2f} p50_s={_percentile(durations, 0.50):.2f} p95_s={_percentile(durations, 0.95):.2f}")
    if queued_ms:
        q_s = [v / 1000.0 for v in queued_ms]
        print(f"queue_wait_s(p50/p95)={_percentile(q_s, 0.50):.2f}/{_percentile(q_s, 0.95):.2f} (n={len(queued_ms)})")
    if processing_s:
        print(f"processing_s(p50/p95)={_percentile(processing_s, 0.50):.2f}/{_percentile(processing_s, 0.95):.2f} (n={len(processing_s)})")

    status_counts: Dict[str, int] = {}
    for r in results:
        status = str(r.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    print("status_counts=", status_counts)

    after_stats = _fetch_queue_stats(warm, args.base_url)
    if after_stats:
        print("queue_stats_after=", after_stats)


if __name__ == "__main__":
    main()
