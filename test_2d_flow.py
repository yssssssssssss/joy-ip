
import requests
import time
import json

BASE_URL = "http://localhost:28888"

def test_2d_flow():
    print("=== Testing 2D Flow ===")
    
    # 1. Test Analyze
    print("\n1. Testing /api/analyze with mode='2D'...")
    analyze_payload = {
        "requirement": "一个帅气的机器人",
        "mode": "2D",
        "perspective": "正视角"
    }
    try:
        res = requests.post(f"{BASE_URL}/api/analyze", json=analyze_payload)
        res_data = res.json()
        print(f"Analyze Response: {json.dumps(res_data, indent=2, ensure_ascii=False)}")
        
        if not res_data.get('success'):
            print("Analyze failed")
            return
        
        analysis = res_data.get('analysis', {})
        if '视角' in analysis:
            print("SUCCESS: Analysis result contains '视角' field.")
        else:
            print("FAILURE: Analysis result MISSING '视角' field.")
            
    except Exception as e:
        print(f"Analyze request failed: {e}")
        return

    # 2. Test Start Generate
    print("\n2. Testing /api/start_generate with mode='2D'...")
    start_payload = {
        "requirement": "一个帅气的机器人",
        "analysis": analysis,
        "mode": "2D",
        "perspective": "正视角"
    }
    
    try:
        res = requests.post(f"{BASE_URL}/api/start_generate", json=start_payload)
        res_data = res.json()
        print(f"Start Generate Response: {json.dumps(res_data, indent=2, ensure_ascii=False)}")
        
        if not res_data.get('success'):
            print("Start Generate failed")
            return
            
        job_id = res_data.get('job_id')
        print(f"Job ID: {job_id}")
        
        # 3. Check Job Status
        print("\n3. Checking Job Status...")
        for _ in range(5):
            time.sleep(1)
            res = requests.get(f"{BASE_URL}/api/job/{job_id}/status")
            job_data = res.json().get('job', {})
            # We can't easily see the internal 'mode' of the job from public API unless it's returned.
            # But we can check logs or behavior.
            print(f"Job Status: {job_data.get('status')}, Progress: {job_data.get('progress')}")
            
    except Exception as e:
        print(f"Start Generate request failed: {e}")

if __name__ == "__main__":
    test_2d_flow()
