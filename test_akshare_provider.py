
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.quant.data_provider import get_data_provider

def test_provider():
    print("Testing DataProvider Factory...")
    provider = get_data_provider()
    print(f"Got provider: {type(provider).__name__}")
    
    if type(provider).__name__ == "MockDataProvider":
        print("Warning: Still using MockDataProvider. AkShare might have failed to init.")
        return

    print("\nTesting get_history for 600519 (Moutai)...")
    # Recent 5 days
    import datetime
    end = datetime.datetime.now().strftime("%Y%m%d")
    start = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y%m%d")
    
    history = provider.get_history("600519", start, end)
    print(f"Fetched {len(history)} records.")
    if history:
        print("Sample record:", history[0])
        
    print("\nTesting get_snapshot for 600519...")
    snapshot = provider.get_snapshot("600519")
    print("Snapshot:", snapshot)

if __name__ == "__main__":
    test_provider()
