
import requests
import os
import sys

def test_network():
    print("Testing network connectivity...")
    
    # 1. Check Environment Variables
    print(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY')}")
    print(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")
    print(f"NO_PROXY: {os.environ.get('NO_PROXY')}")
    
    # 2. Test Baidu (Domestic) - Direct
    print("\n--- Testing Baidu (Direct) ---")
    try:
        resp = requests.get("https://www.baidu.com", timeout=5)
        print(f"Baidu Status: {resp.status_code}")
    except Exception as e:
        print(f"Baidu Failed: {e}")

    # 3. Test EastMoney (Target) - Direct
    # URL derived from AkShare source or common knowledge
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
    print(f"\n--- Testing EastMoney ({url[:40]}...) ---")
    
    # Try with NO_PROXY set in session
    session = requests.Session()
    session.trust_env = False # Ignore env proxies for this test
    
    try:
        print("Attempting connection (ignoring system proxy)...")
        resp = session.get(url, timeout=5)
        print(f"EastMoney Status: {resp.status_code}")
        if resp.status_code == 200:
            print("EastMoney Response (snippet):", resp.text[:100])
    except Exception as e:
        print(f"EastMoney Failed (No Proxy): {e}")
        
    # Try WITH system proxy (if any)
    print("\n--- Testing EastMoney (With System Proxy if set) ---")
    try:
        resp = requests.get(url, timeout=5)
        print(f"EastMoney Status (System Proxy): {resp.status_code}")
    except Exception as e:
        print(f"EastMoney Failed (System Proxy): {e}")

if __name__ == "__main__":
    test_network()
