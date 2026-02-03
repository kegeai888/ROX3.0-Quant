import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class DataManager:
    """
    Local Data Center Manager
    Responsible for saving and loading market data to/from local disk (CSV).
    """
    
    def __init__(self, base_dir: str = "data/market_data"):
        self.base_dir = base_dir
        self._ensure_dirs()
        
    def _ensure_dirs(self):
        """Ensure data directories exist."""
        for period in ["daily", "weekly", "monthly", "minute"]:
            os.makedirs(os.path.join(self.base_dir, period), exist_ok=True)
            
    def _get_file_path(self, symbol: str, period: str) -> str:
        return os.path.join(self.base_dir, period, f"{symbol}.csv")
        
    def save_kline(self, symbol: str, data: List[Dict], period: str = "daily") -> bool:
        """
        Save K-line data to local CSV.
        
        Args:
            symbol: Stock symbol (e.g., '600000')
            data: List of dicts or list of objects that can be converted to DataFrame
            period: 'daily', 'weekly', etc.
        """
        try:
            if not data:
                return False
                
            # Convert to DataFrame
            # Assuming data is list of PricePoint objects or dicts
            # If it's PricePoint objects, we need to convert them
            if hasattr(data[0], '__dict__'):
                rows = [vars(d) for d in data]
            else:
                rows = data
                
            df = pd.DataFrame(rows)
            
            # Ensure consistent columns
            # Standard columns: date, open, close, high, low, volume
            # But DataProvider might use different names. 
            # We will just save what we get, but ensure 'date' is present.
            
            file_path = self._get_file_path(symbol, period)
            df.to_csv(file_path, index=False, encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"Failed to save local data for {symbol}: {e}")
            return False
            
    def load_kline(self, symbol: str, period: str = "daily", max_age_hours: int = 24) -> Optional[List[Dict]]:
        """
        Load K-line data from local CSV if it exists and is not too old.
        
        Args:
            symbol: Stock symbol
            period: Data period
            max_age_hours: Max age of the file in hours. If 0, ignore age check.
            
        Returns:
            List of dicts or None if not found/expired.
        """
        file_path = self._get_file_path(symbol, period)
        
        if not os.path.exists(file_path):
            return None
            
        # Check file age
        if max_age_hours > 0:
            mtime = os.path.getmtime(file_path)
            file_time = datetime.fromtimestamp(mtime)
            if datetime.now() - file_time > timedelta(hours=max_age_hours):
                logger.info(f"Local data for {symbol} is expired (>{max_age_hours}h).")
                return None
                
        try:
            df = pd.read_csv(file_path)
            # Convert NaN to None for JSON compatibility
            df = df.where(pd.notnull(df), None)
            return df.to_dict(orient='records')
        except Exception as e:
            logger.error(f"Failed to load local data for {symbol}: {e}")
            return None

    def is_local_data_available(self, symbol: str, period: str = "daily") -> bool:
        return os.path.exists(self._get_file_path(symbol, period))
