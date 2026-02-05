#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke test for head CLIP query enrichment.

Goal:
- Verify user input can be converted into an English CLIP query.
- Verify the English query is used to retrieve the expected image.

Notes:
- Runs fully offline (no external network).
- Uses a deterministic fake CLIP model so the expected image is stable.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import torch
from PIL import Image


def _setup_env():
    # Prevent background preload that may try to download models.
    os.environ.setdefault("DISABLE_CLIP_PRELOAD", "1")
    # Ensure no network calls are made.
    os.environ.setdefault("OFFLINE_MODE", "1")


def _setup_path():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


class FakeClipModel:
    """
    A tiny deterministic model:
    - Text: maps 'happy' -> [1,0], 'angry' -> [0,1]
    - Image: uses top-left pixel; red-ish -> [1,0], blue-ish -> [0,1]
    """

    def __init__(self):
        self.max_seq_length = 77

    def _vec_for_text(self, text: str) -> torch.Tensor:
        s = (text or "").lower()
        if "angry" in s:
            return torch.tensor([0.0, 1.0])
        if "happy" in s or "smile" in s or "laugh" in s:
            return torch.tensor([1.0, 0.0])
        return torch.tensor([0.5, 0.5])

    def _vec_for_image(self, img: Image.Image) -> torch.Tensor:
        r, g, b = img.getpixel((0, 0))
        if r > b:
            return torch.tensor([1.0, 0.0])
        return torch.tensor([0.0, 1.0])

    def encode(self, items, convert_to_tensor=False, normalize_embeddings=False, **kwargs):
        if isinstance(items, (str, bytes)):
            items = [items]
        vecs: list[torch.Tensor] = []
        for it in list(items or []):
            if isinstance(it, str):
                v = self._vec_for_text(it)
            else:
                v = self._vec_for_image(it)
            if normalize_embeddings:
                n = torch.norm(v)
                if n > 0:
                    v = v / n
            vecs.append(v)
        out = torch.stack(vecs, dim=0) if vecs else torch.empty((0, 2))
        if convert_to_tensor:
            return out
        return out.cpu().numpy()


def main() -> int:
    _setup_env()
    _setup_path()

    # Import after env setup.
    from matchers.head_matcher import HeadMatcher

    tmp_dir = Path("output/_head_clip_query_enrich_test")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    happy_path = tmp_dir / "happy.png"
    angry_path = tmp_dir / "angry.png"

    Image.new("RGB", (32, 32), (255, 0, 0)).save(happy_path)
    Image.new("RGB", (32, 32), (0, 0, 255)).save(angry_path)

    matcher = HeadMatcher()

    # Force our fake CLIP model.
    matcher._clip_model_ref = FakeClipModel()
    matcher._ensure_clip_model = lambda: None

    # Simulate LLM output: “整段中文描述 → 英文检索短语(补全)”
    def fake_call_ai(system_prompt: str, user_prompt: str, temperature=0.3, max_tokens=500, **kwargs) -> str:
        merged = f"{system_prompt}\n{user_prompt}"
        if "生气" in merged or "愤怒" in merged:
            en = "an angry face, frowning"
            expr = "生气"
        else:
            en = "a happy face, squinting eyes, open mouth"
            expr = "开心"
        return (
            "眼睛形状：眯眼\n"
            "嘴型：张嘴\n"
            f"表情：{expr}\n"
            "脸部动态：自然\n"
            "情感强度：中等\n"
            f"英文检索：{en}\n"
        )

    matcher._call_ai = fake_call_ai

    cases = [
        ("一个开心的表情，眯眼，张嘴", "happy.png", "happy"),
        ("一个生气的表情，皱眉", "angry.png", "angry"),
    ]

    for req, expect_name, expect_token in cases:
        feats = matcher.analyze_user_requirement(req)
        en_query = feats.get("英文检索", "")
        assert en_query, f"missing en_query for req={req!r}"
        assert re.search(r"[A-Za-z]", en_query), f"en_query not english: {en_query!r}"
        assert expect_token in en_query.lower(), f"en_query not expected: {en_query!r}"

        query = matcher._build_clip_query_text(req, feats)
        assert re.search(r"[A-Za-z]", query), f"final query not english: {query!r}"

        results, _logs = matcher.find_best_matches_from_folder(req, str(tmp_dir), top_k=1)
        assert results, f"no results for req={req!r}"
        got_path = results[0].get("image_path")
        got_name = os.path.basename(got_path or "")
        assert got_name == expect_name, f"expected {expect_name}, got {got_name}"

        print("req_zh:", req)
        print("en_query:", en_query)
        print("clip_query:", query)
        print("top1:", got_name)
        print("---")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
