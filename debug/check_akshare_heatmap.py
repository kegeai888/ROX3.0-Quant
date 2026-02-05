
import akshare as ak
import pandas as pd
import time

def check_heatmap_data():
    print("Fetching Spot Data...")
    t0 = time.time()
    # stock_zh_a_spot_em returns: 序号, 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, 振幅, 最高, 最低, 今开, 昨收, 量比, 换手率, 市盈率-动态, 市净率, 总市值, 流通市值, 涨速, 5分钟涨跌, 60日涨跌幅, 年初至今涨跌幅
    df = ak.stock_zh_a_spot_em()
    print(f"Fetched {len(df)} rows in {time.time() - t0:.2f}s")
    print("Columns:", df.columns.tolist())
    
    # Check if we have Sector/Industry info directly
    # Usually spot_em DOES NOT have industry. We need to fetch industry list or map separately.
    
    # Let's try to fetch industry boards
    print("\nFetching Industry Boards...")
    t1 = time.time()
    df_industry = ak.stock_board_industry_name_em()
    print(f"Fetched {len(df_industry)} industries in {time.time() - t1:.2f}s")
    print("Industry Columns:", df_industry.columns.tolist())
    # Expected: 排名, 板块名称, 板块代码, 最新价, 涨跌幅...
    
    # To map Stock -> Industry, we might need `stock_board_industry_cons_em` for ALL industries (Too slow?)
    # Or maybe there's a `stock_info_a_code_name` that has industry?
    
    # Alternative: Use "Concept" or just show "Sector Heatmap" first (Sector size by total cap).
    
    # Let's check if we can get a simple Stock->Industry map efficiently.
    # ak.stock_board_industry_summary_promo_em() ? 
    
    # For now, let's see what we have.

if __name__ == "__main__":
    try:
        check_heatmap_data()
    except Exception as e:
        print(f"Error: {e}")
