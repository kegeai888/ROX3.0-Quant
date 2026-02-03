
import akshare as ak
import pandas as pd
import asyncio
import datetime

async def test_search():
    print("Testing AkShare search...")
    
    code = "002414"
    
    # 3. Test Hist Data
    print(f"\n3. Fetching Hist Data for {code} (stock_zh_a_hist)...")
    try:
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start_date, end_date=end_date, adjust="qfq")
        print(f"Hist Data Shape: {df.shape}")
        if not df.empty:
            print(f"Latest: \n{df.tail(1)}")
        else:
            print("Hist Data is empty")
    except Exception as e:
        print(f"Hist Data Failed: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_search())
