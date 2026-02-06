import requests
import pandas as pd
import os

# 强制禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

def fetch_sina_batch(codes):
    url = f"http://hq.sinajs.cn/list={','.join(codes)}"
    headers = {"Referer": "http://finance.sina.com.cn/"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = "gbk"
        return resp.text
    except Exception as e:
        print(f"Error: {e}")
        return ""

test_codes = ["sh600000", "sz000001", "sh600519"]
print(f"Fetching {test_codes} from Sina...")
data = fetch_sina_batch(test_codes)
print("Response length:", len(data))
print(data[:500])

# Parse it
lines = data.strip().split('\n')
for line in lines:
    if not line: continue
    parts = line.split('=')
    code = parts[0].split('_')[-1]
    params = parts[1].replace('"', '').split(',')
    if len(params) > 3:
        name = params[0]
        open_price = params[1]
        prev_close = params[2]
        price = params[3]
        print(f"{code}: {name} Price={price} Open={open_price}")
