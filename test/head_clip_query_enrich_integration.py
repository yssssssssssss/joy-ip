#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test for head CLIP query enrichment (real AI + real local CLIP).

What it verifies:
1) User input (中文描述) -> LLM returns an English query in field "英文检索"
2) The English query is used to retrieve the expected image from a folder via CLIP

Prerequisites:
- AI_API_URL / AI_API_KEY configured (e.g. via .env)
- Local CLIP model present at models/clip-ViT-B-32
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _setup_env():
    # Ensure we are not in offline simulation.
    os.environ.pop("OFFLINE_MODE", None)
    # Prevent background preload that may race with tests.
    os.environ.setdefault("DISABLE_CLIP_PRELOAD", "1")

    # This environment may contain a dead proxy (127.0.0.1:9). Drop it for this test.
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "GIT_HTTP_PROXY", "GIT_HTTPS_PROXY"):
        os.environ.pop(k, None)


def _setup_path():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


def _draw_text_image(path: Path, text: str):
    img = Image.new("RGB", (512, 512), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 96)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (512 - w) // 2
    y = (512 - h) // 2
    draw.text((x, y), text, fill=(0, 0, 0), font=font)
    img.save(path)


def main() -> int:
    _setup_env()
    _setup_path()

    from config import get_config
    from matchers.head_matcher import HeadMatcher

    cfg = get_config()
    if not getattr(cfg, "AI_API_KEY", ""):
        print("SKIP: AI_API_KEY is empty")
        return 0

    tmp_dir = Path("output/_head_clip_query_enrich_integration_test")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    happy_path = tmp_dir / "happy.png"
    angry_path = tmp_dir / "angry.png"

    # Recreate to avoid cache issues.
    for p in (happy_path, angry_path):
        try:
            p.unlink()
        except Exception:
            pass

    _draw_text_image(happy_path, "HAPPY")
    _draw_text_image(angry_path, "ANGRY")

    matcher = HeadMatcher()
    original_analyze = matcher.analyze_user_requirement

    cases = [
        ("一个开心的表情，眯眼，张嘴", "happy.png", {"happy", "smile", "smiling", "grin", "laugh", "joy"}),
        ("一个生气的表情，皱眉，撇嘴", "angry.png", {"angry", "mad", "furious", "rage", "frown", "frowning"}),
    ]

    for req_zh, expect_name, expect_tokens in cases:
        feats = original_analyze(req_zh)
        en_query = (feats or {}).get("英文检索") or ""
        assert re.search(r"[A-Za-z]", en_query), f"missing/invalid 英文检索 for req={req_zh!r}: {en_query!r}"

        if not any(t in en_query.lower() for t in expect_tokens):
            raise AssertionError(f"英文检索 seems unexpected for req={req_zh!r}: {en_query!r}")

        # Avoid a second AI call during retrieval.
        matcher.analyze_user_requirement = (lambda _req, _feats=feats: _feats)
        try:
            results, _logs = matcher.find_best_matches_from_folder(req_zh, str(tmp_dir), top_k=1)
        finally:
            matcher.analyze_user_requirement = original_analyze
        assert results, f"no results for req={req_zh!r}"
        got_name = os.path.basename(results[0].get("image_path") or "")
        assert got_name == expect_name, f"expected {expect_name}, got {got_name}"

        print("req_zh:", req_zh)
        print("en_query:", en_query)
        print("top1:", got_name)
        print("---")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
