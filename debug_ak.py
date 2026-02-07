import akshare as ak
try:
    df = ak.stock_fund_flow_concept(symbol="即时")
    print("Columns:", df.columns.tolist())
    if not df.empty:
        print("First row:", df.iloc[0].to_dict())
except Exception as e:
    print(e)
