import requests
import akshare as ak

print("Testing Sina...")
try:
    headers = {
        "Referer": "http://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    resp = requests.get("http://hq.sinajs.cn/list=sh600519", headers=headers, timeout=5)
    print(f"Sina status: {resp.status_code}")
    print(f"Sina content: {resp.text[:100]}")
except Exception as e:
    print(f"Sina failed: {e}")

print("\nTesting AkShare (Eastmoney)...")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"AkShare Spot shape: {df.shape}")
    print(df.head())
except Exception as e:
    print(f"AkShare failed: {e}")
