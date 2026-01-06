#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 /api/start_generate 接口
用于诊断前端报错问题
"""

import requests
import time
import json

BASE_URL = "http://127.0.0.1:28888"

def test_start_generate():
    """测试启动生成任务"""
    print("=" * 60)
    print("测试 /api/start_generate 接口")
    print("=" * 60)
    
    # 测试数据
    test_requirement = "我想生成一个微笑的站姿角色，穿着红色上衣，拿着气球 ip形象"
    
    print(f"\n1. 发送请求...")
    print(f"   URL: {BASE_URL}/api/start_generate")
    print(f"   需求: {test_requirement}")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/start_generate",
            json={"requirement": test_requirement},
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n2. 响应结果:")
        print(f"   状态码: {response.status_code}")
        print(f"   响应时间: {elapsed:.2f}秒")
        print(f"   响应头: {dict(response.headers)}")
        print(f"\n3. 响应内容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200 and response.json().get('success'):
            job_id = response.json().get('job_id')
            print(f"\n✓ 任务启动成功！Job ID: {job_id}")
            
            # 轮询任务状态
            print(f"\n4. 开始轮询任务状态...")
            for i in range(10):
                time.sleep(2)
                status_response = requests.get(
                    f"{BASE_URL}/api/job/{job_id}/status",
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    job_data = status_response.json().get('job', {})
                    status = job_data.get('status')
                    progress = job_data.get('progress', 0)
                    stage = job_data.get('stage', '')
                    
                    print(f"   [{i+1}] 状态: {status}, 进度: {progress}%, 阶段: {stage}")
                    
                    if status in ['succeeded', 'failed']:
                        print(f"\n5. 任务完成！")
                        print(json.dumps(job_data, indent=2, ensure_ascii=False))
                        break
                else:
                    print(f"   查询状态失败: {status_response.status_code}")
        else:
            print(f"\n✗ 任务启动失败！")
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"\n✗ 请求超时！({elapsed:.2f}秒)")
        print("   这可能是导致前端报错的原因")
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求异常: {str(e)}")
        
    except Exception as e:
        print(f"\n✗ 未知错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_start_generate()
