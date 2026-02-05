#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地（无监听端口）压测脚本：用 Flask test_client 直接调用接口。
适用场景：Windows 沙箱/权限导致无法 bind 端口时，仍可评估 Job 队列并发与链路耗时。

默认行为：analyze(async) -> poll -> start_generate -> poll

示例：
  python test/perf/local_load_test.py --concurrency 5 --requests 20
  python test/perf/local_load_test.py --concurrency 10 --requests 50 --skip-analyze
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import sys
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List


_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


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


def _poll_job(app, job_id: str, timeout_s: int = 600) -> Dict[str, Any]:
    start = time.time()
    while True:
        if time.time() - start > timeout_s:
            return {"success": False, "status": "timeout", "job_id": job_id}
        with app.test_client() as c:
            r = c.get(f"/api/job/{job_id}/status")
            data = r.get_json(silent=True) or {}
        if not data.get("success"):
            time.sleep(0.05)
            continue
        job = data.get("job") or {}
        status = job.get("status")
        if status in ("succeeded", "failed", "cancelled"):
            return {"success": True, "status": status, "job": job}
        time.sleep(0.05)


def _one_request(app, requirement: str, skip_analyze: bool, mode: str, perspective: str) -> Dict[str, Any]:
    t0 = time.perf_counter()

    analysis = None
    analysis_override = os.environ.get("LOAD_TEST_ANALYSIS_JSON")
    if analysis_override and str(analysis_override).strip():
        try:
            analysis = json.loads(str(analysis_override))
            if not isinstance(analysis, dict):
                analysis = None
        except Exception:
            analysis = None

    if analysis is None and not skip_analyze:
        with app.test_client() as c:
            a_resp = c.post(
                "/api/analyze",
                json={"requirement": requirement, "mode": mode, "perspective": perspective, "async": True},
            )
            a = a_resp.get_json(silent=True) or {}
        if not a.get("success") or not a.get("job_id"):
            return {"ok": False, "duration_s": time.perf_counter() - t0, "status": "analyze_start_failed", "raw": a}
        analyze_job_id = a["job_id"]
        analyze_res = _poll_job(app, analyze_job_id, timeout_s=180)
        if analyze_res.get("status") != "succeeded":
            return {
                "ok": False,
                "duration_s": time.perf_counter() - t0,
                "status": f"analyze_{analyze_res.get('status')}",
                "analyze_job": analyze_res.get("job"),
            }
        analysis = (analyze_res.get("job") or {}).get("analysis")
        if not isinstance(analysis, dict):
            return {"ok": False, "duration_s": time.perf_counter() - t0, "status": "analyze_no_analysis"}

    payload: Dict[str, Any] = {"requirement": requirement, "mode": mode}
    if mode == "2D":
        payload["perspective"] = perspective
    if isinstance(analysis, dict):
        payload["analysis"] = analysis

    with app.test_client() as c:
        s_resp = c.post("/api/start_generate", json=payload)
        s = s_resp.get_json(silent=True) or {}
        http_status = int(getattr(s_resp, "status_code", 0) or 0)

    if not s.get("success") or not s.get("job_id"):
        code = s.get("code") or f"HTTP_{http_status or 0}"
        return {
            "ok": False,
            "duration_s": time.perf_counter() - t0,
            "status": f"start_generate_{code}",
            "code": code,
            "raw": s,
        }

    job_id = s["job_id"]
    gen_res = _poll_job(app, job_id, timeout_s=600)
    status = gen_res.get("status")
    job = gen_res.get("job") or {}
    timings = job.get("stage_timings") or {}

    return {
        "ok": status == "succeeded",
        "duration_s": time.perf_counter() - t0,
        "status": str(status),
        "job_id": job_id,
        "job_stage": str(job.get("stage") or ""),
        "job_error": str(job.get("error") or ""),
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
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--skip-analyze", action="store_true")
    parser.add_argument("--analysis-json", default="", help="直接注入 start_generate 的 analysis（JSON字符串），用于压测完整链路")
    parser.add_argument("--mode", default="3D", choices=["2D", "3D"])
    parser.add_argument("--perspective", default="正视角", choices=["正视角", "仰视角"])
    parser.add_argument("--requirement", default="一个开心站立的角色，穿红色上衣，戴帽子，手拿气球")
    args = parser.parse_args()

    # 离线模式（用于本地压测：禁用外网 LLM/Gate）
    os.environ.setdefault("OFFLINE_MODE", "1")
    os.environ.setdefault("ENABLE_GATE_CHECK", "0")
    os.environ.setdefault("GATE_CHECK_SCOPE", "none")
    os.environ.setdefault("OFFLINE_LLM_LATENCY_MS", "0")
    os.environ.setdefault("OFFLINE_IMAGE_LATENCY_MS", "0")
    os.environ.setdefault("OFFLINE_GATE_LATENCY_MS", "0")

    if args.analysis_json and str(args.analysis_json).strip():
        os.environ["LOAD_TEST_ANALYSIS_JSON"] = str(args.analysis_json).strip()

    print("==== local_load_test ====")
    print(f"concurrency={args.concurrency} requests={args.requests} skip_analyze={args.skip_analyze}")
    print(f"mode={args.mode} perspective={args.perspective}")
    print("=========================")

    from app_new import app  # noqa: WPS433 (runtime import for env overrides)
    from utils.job_manager import job_manager

    try:
        print("queue_stats=", job_manager.get_queue_stats())
    except Exception as e:
        print("queue_stats_error=", str(e))

    # warmup 1 次（避免首请求包含大量初始化）
    try:
        _one_request(app, args.requirement, args.skip_analyze, args.mode, args.perspective)
    except Exception:
        pass

    t0 = time.perf_counter()
    results: List[Dict[str, Any]] = []

    with futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [
            ex.submit(_one_request, app, args.requirement, args.skip_analyze, args.mode, args.perspective)
            for _ in range(args.requests)
        ]
        for f in futures.as_completed(futs):
            results.append(f.result())

    total_s = time.perf_counter() - t0
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
        st = str(r.get("status") or "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1
    print("status_counts=", status_counts)

    if fail_count:
        fail_reasons: Dict[str, int] = {}
        examples: List[Dict[str, Any]] = []
        for r in results:
            if r.get("ok"):
                continue
            stage = str(r.get("job_stage") or "")
            err = str(r.get("job_error") or "")
            err_one = (err.splitlines()[0] if err else "").strip()
            key = str(r.get("status") or "unknown")
            if stage:
                key = f"{key}@{stage}"
            if err_one:
                key = f"{key}: {err_one[:160]}"
            fail_reasons[key] = fail_reasons.get(key, 0) + 1
            if len(examples) < 3:
                examples.append(
                    {
                        "job_id": r.get("job_id"),
                        "status": r.get("status"),
                        "stage": stage,
                        "error": err_one[:200],
                    }
                )
        print("fail_reasons=", fail_reasons)
        print("fail_examples=", examples)


if __name__ == "__main__":
    main()
