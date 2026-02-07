import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rox_quant.data_provider import DataProvider

def test_multi_asset():
    dp = DataProvider()
    
    print("-" * 30)
    print("Testing Crypto (BTC/USDT)...")
    try:
        quote = dp.get_realtime_quote("BTC/USDT")
        print(f"Quote: {quote}")
        
        hist = dp.get_history("BTC/USDT", days=5)
        print(f"History (last 2): {hist[-2:] if hist else 'Empty'}")
        
        if quote and quote.get('price', 0) > 0 and hist:
            print("✅ Crypto Test Passed")
        else:
            print("❌ Crypto Test Failed (No data)")
    except Exception as e:
        print(f"❌ Crypto Test Error: {e}")

    print("-" * 30)
    print("Testing Global (AAPL)...")
    try:
        quote = dp.get_realtime_quote("AAPL")
        print(f"Quote: {quote}")
        
        hist = dp.get_history("AAPL", days=5)
        print(f"History (last 2): {hist[-2:] if hist else 'Empty'}")
        
        if quote and quote.get('price', 0) > 0 and hist:
            print("✅ Global Test Passed")
        else:
            print("❌ Global Test Failed (No data)")
    except Exception as e:
        print(f"❌ Global Test Error: {e}")

if __name__ == "__main__":
    test_multi_asset()
