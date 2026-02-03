
import akshare as ak
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

def test_index():
    symbol = "sh000001"
    try:
        print(f"Fetching {symbol} via daily...")
        # df = ak.stock_zh_index_daily_em(symbol=symbol)
        # print("Success daily!")
    except Exception as e:
        print(f"Failed daily: {e}")

    try:
        print("Fetching spot...")
        df_spot = ak.stock_zh_index_spot()
        print("Success spot!")
        print(df_spot.head())
        # Check if sh000001 is in it
        # Usually it has '代码' column. 000001?
        print(df_spot[df_spot['代码'] == '000001'])
    except Exception as e:
        print(f"Failed spot: {e}")

if __name__ == "__main__":
    test_index()
