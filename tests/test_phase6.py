import sys
import os
import asyncio
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)

def test_macro_indicators():
    print(">>> Testing Macro API")
    try:
        response = client.get("/api/macro/indicators")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GDP: {data.get('gdp')}")
            print(f"✅ CPI: {data.get('cpi')}")
            print(f"✅ M1/M2 Data Count: {len(data.get('money_supply', []))}")
        else:
            print(f"❌ Macro API Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Macro Exception: {e}")

def test_info_news():
    print("\n>>> Testing News API")
    try:
        response = client.get("/api/info/news?limit=3")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ News Items: {len(data)}")
            if data:
                print(f"   Sample: {data[0]['title']}")
        else:
            print(f"❌ News API Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ News Exception: {e}")

def test_concepts():
    print("\n>>> Testing Concepts API")
    try:
        response = client.get("/api/market/heat") # Checking existing one first
        print("   (Checked /market/heat for context)")
        
        response = client.get("/api/market/concepts")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Concepts Found: {len(data)}")
            if data:
                print(f"   Top Concept: {data[0]['name']} (Net: {data[0]['net_inflow']})")
        else:
            print(f"❌ Concepts API Failed: {response.status_code} (Might not be implemented yet)")
    except Exception as e:
        print(f"❌ Concepts Exception: {e}")

if __name__ == "__main__":
    test_macro_indicators()
    test_info_news()
    test_concepts()
