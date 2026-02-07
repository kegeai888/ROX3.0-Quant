import os
import json
import zipfile
import shutil
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.db import get_db_context, DB_PATH
from app.core.config import settings

class SyncManager:
    """
    Manages full system backup and restore (Watchlist, Trades, Settings, Strategies).
    Format: ZIP file containing:
      - tables/*.json (DB dumps)
      - strategies/*.py (User strategies)
      - meta.json (Version info)
    """
    
    TEMP_DIR = os.path.join(settings.DATA_DIR, "sync_temp")
    STRATEGIES_DIR = os.path.join(settings.BASE_DIR, "app/strategies")
    
    def __init__(self):
        os.makedirs(self.TEMP_DIR, exist_ok=True)
        
    def create_backup_zip(self, user_id: int) -> str:
        """
        Creates a zip backup for the given user.
        Returns: Absolute path to the zip file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"rox_backup_{user_id}_{timestamp}"
        work_dir = os.path.join(self.TEMP_DIR, backup_name)
        os.makedirs(work_dir, exist_ok=True)
        
        try:
            # 1. Export DB Tables
            tables_dir = os.path.join(work_dir, "tables")
            os.makedirs(tables_dir, exist_ok=True)
            
            with get_db_context() as conn:
                self._dump_table(conn, "watchlist", user_id, tables_dir)
                self._dump_table(conn, "trades", user_id, tables_dir)
                self._dump_table(conn, "alerts", user_id, tables_dir)
                # Accounts are critical.
                self._dump_table(conn, "accounts", user_id, tables_dir)
                # Strategies (Visual)
                self._dump_table(conn, "visual_strategies", user_id, tables_dir)
                
            # 2. Export Python Strategies
            # Copy all .py files in strategies dir (assuming they are user's)
            # In a multi-user system, we might need filtering, but for ROX desktop single/few user is fine.
            strat_dest = os.path.join(work_dir, "strategies")
            os.makedirs(strat_dest, exist_ok=True)
            if os.path.exists(self.STRATEGIES_DIR):
                for f in os.listdir(self.STRATEGIES_DIR):
                    if f.endswith(".py") and f != "__init__.py":
                        shutil.copy2(os.path.join(self.STRATEGIES_DIR, f), strat_dest)
                        
            # 3. Meta
            meta = {
                "version": "1.0",
                "created_at": timestamp,
                "user_id": user_id,
                "platform": "ROX 3.0"
            }
            with open(os.path.join(work_dir, "meta.json"), "w", encoding='utf-8') as f:
                json.dump(meta, f, indent=2)
                
            # 4. Zip
            zip_path = os.path.join(self.TEMP_DIR, f"{backup_name}.zip")
            self._zip_folder(work_dir, zip_path)
            
            return zip_path
        finally:
            # Cleanup temp work dir
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)

    def restore_backup(self, zip_path: str, user_id: int) -> bool:
        """
        Restores data from zip.
        Strategy: MERGE (Insert if not exists by business key or ID if preserved).
        Currently implements simple overwrite/append based on ID conflict? 
        Better: reset local tables? No, that's dangerous.
        Safe approach: Append new items, ignore duplicates.
        """
        extract_dir = os.path.join(self.TEMP_DIR, "restore_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)
                
            # 1. Restore DB
            tables_dir = os.path.join(extract_dir, "tables")
            if os.path.exists(tables_dir):
                with get_db_context() as conn:
                    # Watchlist
                    self._restore_table(conn, "watchlist", os.path.join(tables_dir, "watchlist.json"), user_id, keys=["stock_code"])
                    # Trades (duplicates check by open_time + symbol?)
                    self._restore_table(conn, "trades", os.path.join(tables_dir, "trades.json"), user_id, keys=["open_time", "symbol"])
                    # Visual Strategies
                    self._restore_table(conn, "visual_strategies", os.path.join(tables_dir, "visual_strategies.json"), user_id, keys=["name"])

            # 2. Restore Python Strategies
            strat_src = os.path.join(extract_dir, "strategies")
            if os.path.exists(strat_src):
                os.makedirs(self.STRATEGIES_DIR, exist_ok=True)
                for f in os.listdir(strat_src):
                    if f.endswith(".py"):
                        src = os.path.join(strat_src, f)
                        dst = os.path.join(self.STRATEGIES_DIR, f)
                        # Overwrite if exists? Strategy files are simpler to just overwrite or skip.
                        # Let's overwrite to ensure latest version from "Cloud".
                        shutil.copy2(src, dst)
                        
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            return False
        finally:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)

    def _dump_table(self, conn: sqlite3.Connection, table: str, user_id: int, out_dir: str):
        try:
            # Check if user_id column exists? Most tables have it.
            cur = conn.execute(f"SELECT * FROM {table} WHERE user_id = ?", (user_id,))
            rows = [dict(row) for row in cur.fetchall()]
            
            out_path = os.path.join(out_dir, f"{table}.json")
            with open(out_path, "w", encoding='utf-8') as f:
                json.dump(rows, f, default=str, indent=2) # default=str handles datetime
        except Exception as e:
            print(f"Failed to dump table {table}: {e}")

    def _restore_table(self, conn: sqlite3.Connection, table: str, json_path: str, user_id: int, keys: List[str]):
        if not os.path.exists(json_path):
            return
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                rows = json.load(f)
                
            for row in rows:
                # Ensure user_id matches target (if we are syncing to same user)
                row['user_id'] = user_id
                
                # Check duplicate
                where_clause = " AND ".join([f"{k} = ?" for k in keys])
                params = [row[k] for k in keys]
                sql_check = f"SELECT id FROM {table} WHERE user_id = ? AND {where_clause}"
                cur = conn.execute(sql_check, [user_id] + params)
                existing = cur.fetchone()
                
                if not existing:
                    # Insert
                    # Remove 'id' to let autoincrement work, or keep it?
                    # Generally safely to drop 'id' and create new record to avoid PK collision.
                    if 'id' in row: del row['id']
                    
                    cols = ", ".join(row.keys())
                    placeholders = ", ".join(["?"] * len(row))
                    vals = list(row.values())
                    conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", vals)
            
            conn.commit()
        except Exception as e:
            print(f"Failed to restore {table}: {e}")

    def _zip_folder(self, folder_path, output_path):
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zf.write(file_path, arcname)
