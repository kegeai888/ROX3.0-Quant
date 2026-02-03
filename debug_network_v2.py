
import requests
import os
import sys

def test_network():
    print("Testing network connectivity with Headers...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive"
    }
    
    # 1. Test Sina (Alternative Source)
    print("\n--- Testing Sina (http://hq.sinajs.cn/list=sh000001) ---")
    try:
        resp = requests.get("http://hq.sinajs.cn/list=sh000001", headers=headers, timeout=5)
        print(f"Sina Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Sina Response:", resp.text[:50])
    except Exception as e:
        print(f"Sina Failed: {e}")

    # 2. Test EastMoney (Target) - With Headers
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
    print(f"\n--- Testing EastMoney ({url[:40]}...) ---")
    
    # Try Direct (NO_PROXY)
    session = requests.Session()
    session.trust_env = False 
    
    try:
        print("Attempting EastMoney (Direct + Headers)...")
        resp = session.get(url, headers=headers, timeout=5)
        print(f"EastMoney Status: {resp.status_code}")
        if resp.status_code == 200:
            print("EastMoney Response (snippet):", resp.text[:100])
    except Exception as e:
        print(f"EastMoney Failed (Direct): {e}")
        
    # Try System Proxy
    try:
        print("\nAttempting EastMoney (System Proxy + Headers)...")
        resp = requests.get(url, headers=headers, timeout=5)
        print(f"EastMoney Status: {resp.status_code}")
    except Exception as e:
        print(f"EastMoney Failed (Proxy): {e}")

if __name__ == "__main__":
    test_network()
