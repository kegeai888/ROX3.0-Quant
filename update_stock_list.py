import akshare as ak
import pandas as pd
import os

# 强制禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

print("Fetching full stock list...")
try:
    df = ak.stock_info_a_code_name()
    if df is None or df.empty:
        print("Failed to fetch stock list.")
        exit(1)
        
    print(f"Fetched {len(df)} stocks.")
    print("Columns:", df.columns.tolist())
    
    # 确保列名符合要求
    # akshare通常返回 'code', 'name'
    if 'code' in df.columns:
        df = df.rename(columns={'code': '代码', 'name': '名称'})
        
    # 只保留代码和名称
    if '代码' in df.columns and '名称' in df.columns:
        df = df[['代码', '名称']]
        
        # 补全代码为6位
        df['代码'] = df['代码'].astype(str).str.zfill(6)
        
        output_path = 'app/static/stock_list.csv'
        df.to_csv(output_path, index=False)
        print(f"Saved to {output_path}")
    else:
        print("Required columns not found.")
        
except Exception as e:
    print(f"Error: {e}")
