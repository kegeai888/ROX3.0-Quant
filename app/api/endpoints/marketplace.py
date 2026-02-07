from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import sqlite3
from app.db import get_db
from app.auth import get_current_user, User
import os
import shutil

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])

@router.get("/list")
async def list_marketplace_items(
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    List all available strategies in the marketplace.
    """
    cur = conn.execute("SELECT * FROM marketplace_items ORDER BY install_count DESC")
    return [dict(row) for row in cur.fetchall()]

@router.post("/install/{item_id}")
async def install_strategy(
    item_id: int,
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Install a strategy from marketplace to local strategies folder.
    """
    # 1. Get Item info
    cur = conn.execute("SELECT * FROM marketplace_items WHERE id = ?", (item_id,))
    item = cur.fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    item = dict(item)
    
    # 2. Simulate Cloud Download
    # In a real app, this would download from S3/CDN.
    # Here we mock it by copying from a "seed" location or creating a dummy file if not exists.
    
    # Target path
    target_dir = "app/strategies"
    os.makedirs(target_dir, exist_ok=True)
    
    # Source path (mock)
    # If seeding via script didn't create real files, we'll create a dummy one on the fly.
    filename = os.path.basename(item['file_path'])
    target_path = os.path.join(target_dir, filename)
    
    if os.path.exists(target_path):
        return {"status": "already_installed", "message": f"{filename} already exists"}
        
    # Generate Helper Content
    content = f"""
class {item['name'].replace(' ', '')}Strategy:
    '''
    {item['name']} 
    Author: {item['author']}
    Desc: {item['description']}
    Installed from Marketplace
    '''
    def on_tick(self, tick):
        # Logic for {item['name']}
        pass
"""
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
            
        # 3. Update Install Count
        conn.execute("UPDATE marketplace_items SET install_count = install_count + 1 WHERE id = ?", (item_id,))
        conn.commit()
        
        return {"status": "success", "message": f"Installed {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Install failed: {e}")
