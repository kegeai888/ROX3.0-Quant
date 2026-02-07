import sys
import os
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db_context

def test_marketplace_db():
    print(">>> Testing Marketplace DB")
    with get_db_context() as conn:
        cur = conn.execute("SELECT * FROM marketplace_items")
        rows = cur.fetchall()
        print(f"Found {len(rows)} items in marketplace")
        for row in rows:
            print(f"- {row['name']} by {row['author']}")
            
        if len(rows) > 0:
            print("✅ Marketplace seeded successfully")
        else:
            print("❌ Marketplace empty")

if __name__ == "__main__":
    test_marketplace_db()
