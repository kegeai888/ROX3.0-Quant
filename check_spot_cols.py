
import akshare as ak
try:
    df = ak.stock_zh_a_spot_em()
    print(df.columns)
    print(df.head(1))
except Exception as e:
    print(e)
