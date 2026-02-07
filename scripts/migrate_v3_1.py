import sqlite3
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def migrate():
    print(f"Migrating DB at {settings.DB_PATH}...")
    conn = sqlite3.connect(settings.DB_PATH)
    
    # 1. Create crypto_spot
    print("Creating crypto_spot table...")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS crypto_spot (
            symbol TEXT PRIMARY KEY,
            price REAL,
            change_24h REAL,
            volume_24h REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # 2. Create global_spot
    print("Creating global_spot table...")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS global_spot (
            symbol TEXT PRIMARY KEY,
            price REAL,
            change_pct REAL,
            volume REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # 3. Update watchlist to support asset_type if needed (optional for now, can infer from symbol)
    # Ensure asset_type column exists
    try:
        conn.execute("ALTER TABLE watchlist ADD COLUMN asset_type TEXT DEFAULT 'stock'")
        print("Added asset_type to watchlist")
    except sqlite3.OperationalError:
        print("asset_type already exists in watchlist")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
