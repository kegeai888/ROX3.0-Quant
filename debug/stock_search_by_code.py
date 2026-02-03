import akshare as ak
import pandas as pd

try:
    print("Fetching stock spot data...")
    df = ak.stock_zh_a_spot_em()
    print("Columns:", df.columns.tolist())
    print("First 5 rows:")
    print(df[['代码', '名称']].head(5))
    
    # Check for any stock starting with 000858
    code_match = df[df['代码'] == '000858']
    if not code_match.empty:
        print("Found by code 000858:")
        print(code_match.iloc[0])
        print(f"Name type: {type(code_match.iloc[0]['名称'])}")
        print(f"Name repr: {repr(code_match.iloc[0]['名称'])}")
    else:
        print("Not found by code 000858")

except Exception as e:
    print(f"Error: {e}")