import sys
import os
import shutil
import sqlite3
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rox_quant.sync_manager import SyncManager
from app.db import get_db_context, init_db

def test_sync():
    print(">>> Testing Sync Manager")
    
    # Setup
    manager = SyncManager()
    user_id = 1
    
    # 1. Ensure some dummy data
    print("Preparing DB...")
    with get_db_context() as conn:
        conn.execute("INSERT OR IGNORE INTO watchlist (user_id, stock_code, stock_name) VALUES (?, ?, ?)", (user_id, "TEST999", "Test Stock"))
        conn.commit()
        
    # 2. Backup
    print("Creating Backup...")
    zip_path = manager.create_backup_zip(user_id)
    print(f"Backup created at: {zip_path}")
    
    if os.path.exists(zip_path):
        print("✅ Backup Zip exists")
    else:
        print("❌ Backup Zip missing")
        return

    # 3. Modify DB (Delete item) to verify restore works
    print("Modifying DB (Simulating data loss)...")
    with get_db_context() as conn:
        conn.execute("DELETE FROM watchlist WHERE stock_code = 'TEST999'")
        conn.commit()
        
    # 4. Restore
    print("Restoring Backup...")
    success = manager.restore_backup(zip_path, user_id)
    if success:
        print("✅ Restore reported success")
    else:
        print("❌ Restore reported failure")
        
    # 5. Verify Restore
    with get_db_context() as conn:
        cur = conn.execute("SELECT stock_name FROM watchlist WHERE stock_code = 'TEST999'")
        row = cur.fetchone()
        if row:
            print("✅ Data Restored Successfully")
        else:
            print("❌ Data Restore Failed")
            
    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)

if __name__ == "__main__":
    test_sync()
