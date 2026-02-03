
import akshare as ak
import sys
import time
import os

# Try to bypass proxy
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

def check_akshare():
    print("Starting AkShare check...")
    # List of checks to try in order
    # 1. Shanghai Composite (sh000001)
    # 2. Shanghai Composite (000001)
    # 3. Shenzhen Component (sz399001)
    # 4. General Spot Data (fallback)
    
    last_error = None
    
    # Try specific indices first (lightweight)
    for symbol in ["sh000001", "000001", "sz399001", "399001"]:
        print(f"Trying symbol: {symbol}")
        try:
            res = ak.stock_zh_index_spot_em(symbol=symbol)
            if res is not None and not res.empty:
                print(f"Success with {symbol}!")
                print(res)
                return True
        except Exception as e:
            print(f"Failed with {symbol}: {e} (Type: {type(e)})")
            last_error = e
            continue
    
    # Fallback to general spot data (heavier but reliable)
    print("Trying fallback stock_zh_a_spot_em...")
    try:
        res = ak.stock_zh_a_spot_em()
        if res is not None and not res.empty:
            print("Success with fallback!")
            print(res.head())
            return True
    except Exception as e:
        print(f"Failed with fallback: {e} (Type: {type(e)})")
        last_error = e
        
    # If we get here, all checks failed
    if last_error:
        print(f"Final Error: {last_error}")
        print(f"Final Error str: '{str(last_error)}'")
        raise last_error
    else:
        raise Exception("AkShare connectivity check failed")

if __name__ == "__main__":
    try:
        check_akshare()
        print("Overall Status: OK")
    except Exception as e:
        print(f"Overall Status: Error: {str(e)}")
