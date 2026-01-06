#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试中文翻译为英文后的CLIP检索效果"""

from matchers.head_matcher import HeadMatcher

hm = HeadMatcher()
folder = 'data/face_front_per'

expressions = ['大笑', '微笑', '愤怒', '悲伤', '惊讶', '冷漠']

print('=' * 70)
print('使用英文翻译后的CLIP头像检索测试')
print('=' * 70)

for expr in expressions:
    print(f'\n--- 表情: {expr} ---')
    results, logs = hm.find_best_matches_from_folder(expr, folder, top_k=3)
    if results:
        print(f'Top3结果:')
        for i, r in enumerate(results):
            print(f'  {i+1}. {r["image_name"]} (相似度: {r["score"]:.4f})')
