import akshare as ak
import pandas as pd
import time
import os

# 强制禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'


print("Testing AkShare stock_info_a_code_name...")
try:
    start = time.time()
    df = ak.stock_info_a_code_name()
    print(f"Time taken: {time.time() - start:.2f}s")
    if df is None or df.empty:
        print("Result is empty or None")
    else:
        print(f"Columns: {df.columns.tolist()}")
        print(f"Rows: {len(df)}")
        print(df.head())
except Exception as e:
    print(f"Error: {e}")

