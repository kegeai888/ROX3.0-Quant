
import akshare as ak
import pandas as pd
import asyncio

def normalize_text(text):
    if not text: return ""
    # Mimic what I suspect is in stock_utils.py or simple version
    return str(text).strip()

async def test_search():
    print("Testing AkShare search...")
    
    # 1. Test Spot Data
    print("\n1. Fetching Spot Data (stock_zh_a_spot_em)...")
    try:
        df = ak.stock_zh_a_spot_em()
        print(f"Spot Data Shape: {df.shape}")
        if not df.empty:
            mask = df['名称'].astype(str).str.contains("高德红外")
            match = df[mask]
            print(f"Spot Match: \n{match}")
        else:
            print("Spot Data is empty")
    except Exception as e:
        print(f"Spot Data Failed: {e}")

    # 2. Test Code Name List
    print("\n2. Fetching Code Name List (stock_info_a_code_name)...")
    try:
        name_df = ak.stock_info_a_code_name()
        print(f"Name List Shape: {name_df.shape}")
        if not name_df.empty:
            mask = name_df['name'].astype(str).str.contains("高德红外")
            match = name_df[mask]
            print(f"Name List Match: \n{match}")
        else:
            print("Name List is empty")
    except Exception as e:
        print(f"Name List Failed: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_search())
