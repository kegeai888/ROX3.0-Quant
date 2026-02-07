import sqlite3
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def migrate():
    print(f"Migrating DB (Phase 4) at {settings.DB_PATH}...")
    conn = sqlite3.connect(settings.DB_PATH)
    
    # 1. Marketplace Table
    print("Creating marketplace_items table...")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS marketplace_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            author TEXT NOT NULL,
            description TEXT,
            price REAL DEFAULT 0.0,
            install_count INTEGER DEFAULT 0,
            rating REAL DEFAULT 5.0,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # 2. Add User Profile fields
    print("Updating users table...")
    try:
        cur = conn.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        
        if "avatar" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT '/static/avatars/default.png'")
            print("Added avatar column")
        else:
            print("avatar column exists")
            
        if "bio" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN bio TEXT")
            print("Added bio column")
            
        if "tags" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN tags TEXT")
            print("Added tags column")
            
    except Exception as e:
        print(f"Error updating users: {e}")

    # Seed Marketplace Data (Optional)
    # Check if empty
    cur = conn.execute("SELECT count(*) FROM marketplace_items")
    if cur.fetchone()[0] == 0:
        print("Seeding marketplace...")
        items = [
            ("Grid Master Pro", "Official ROX", "Classic mean-reversion grid strategy. Suitable for oscillating markets.", 0.0, "strategies/grid_master.py"),
            ("Golden Cross", "Community", "Simple SMA Dual Thrust strategy.", 0.0, "strategies/golden_cross.py"),
            ("Turtle Soup", "Legend", "Trend following breakout strategy.", 99.0, "strategies/turtle.py")
        ]
        conn.executemany(
            "INSERT INTO marketplace_items (name, author, description, price, file_path) VALUES (?, ?, ?, ?, ?)",
            items
        )

    conn.commit()
    conn.close()
    print("Migration (Phase 4) complete.")

if __name__ == "__main__":
    migrate()
