
from typing import Optional
import re

def normalize_text(s: str) -> str:
    """
    Normalize company names by removing common suffixes and special characters.
    """
    if not s: return ""
    s = str(s).strip()
    rep = ["股份有限公司", "股份", "集团", "有限公司", "控股", "科技", "产业", "公司", "有限责任公司"]
    for r in rep:
        s = s.replace(r, "")
    s = s.replace(" ", "").replace("（", "(").replace("）", ")")
    return s

def extract_stock_code(query: str) -> Optional[str]:
    """
    Extract 6-digit stock code from query string.
    Supports formats like '600000', 'SH600000', 'sz300001'.
    """
    if not query:
        return None
        
    query = query.strip()
    s_up = query.upper()
    
    # Direct 6-digit match
    m = re.search(r'(\d{6})', s_up)
    if m:
        return m.group(1)
        
    # Remove prefixes and try again
    for p in ["SH", "SZ", "SS", "CSI"]:
        if s_up.startswith(p):
            s_up = s_up[len(p):]
            m2 = re.search(r'(\d{6})', s_up)
            if m2:
                return m2.group(1)
                
    return None

def safe_float(val) -> float:
    """
    Safely convert value to float, handling NaNs and Infs.
    """
    import math
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f): return 0.0
        return f
    except: return 0.0
