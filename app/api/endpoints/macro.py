from fastapi import APIRouter, HTTPException
import akshare as ak
import pandas as pd
from typing import Dict, List, Any
import logging

router = APIRouter(prefix="/macro", tags=["Macro"])
logger = logging.getLogger("rox-macro")

@router.get("/indicators")
async def get_macro_indicators() -> Dict[str, Any]:
    """
    Get key macro indicators: GDP, CPI, PPI, PMI, Money Supply (M1/M2).
    Uses AkShare data.stats.gov.cn interfaces.
    """
    try:
        # 1. Money Supply (M1/M2) - Critical for Liquidity
        # macro_china_money_supply() returns monthly data
        try:
            money_df = ak.macro_china_money_supply()
            # Sort by month desc
            money_df['统计时间'] = pd.to_datetime(money_df['统计时间'])
            money_df = money_df.sort_values('统计时间', ascending=False).head(12) # Last year
            
            # Formulate M1-M2 Scissors
            money_data = []
            for _, row in money_df.iterrows():
                try:
                    m2_yoy = float(row['货币和准货币(M2)同比增长'])
                    m1_yoy = float(row['货币(M1)同比增长'])
                    money_data.append({
                        "date": row['统计时间'].strftime("%Y-%m"),
                        "m2_yoy": m2_yoy,
                        "m1_yoy": m1_yoy,
                        "scissors": round(m1_yoy - m2_yoy, 2)
                    })
                except:
                    continue
        except Exception as e:
            logger.error(f"Error fetching Money Supply: {e}")
            money_data = []

        # 2. PMI (Manufacturing) - Critical for Economy
        try:
            pmi_df = ak.macro_china_pmi()
            pmi_df['统计时间'] = pd.to_datetime(pmi_df['统计时间'])
            pmi_df = pmi_df.sort_values('统计时间', ascending=False).head(12)
            
            pmi_data = []
            for _, row in pmi_df.iterrows():
                 pmi_data.append({
                    "date": row['统计时间'].strftime("%Y-%m"),
                    "manufacturing": float(row['制造业']),
                    "non_manufacturing": float(row['非制造业'])
                })
        except Exception as e:
            logger.error(f"Error fetching PMI: {e}")
            pmi_data = []
            
        # 3. CPI/PPI
        try:
            cpi_df = ak.macro_china_cpi() # Monthly
            cpi_df['统计时间'] = pd.to_datetime(cpi_df['统计时间'])
            cpi_last = cpi_df.sort_values('统计时间', ascending=False).iloc[0]
            cpi_val = float(cpi_last['全国-同比'])
            cpi_date = cpi_last['统计时间'].strftime("%Y-%m")
            
            ppi_df = ak.macro_china_ppi() # Monthly
            ppi_df['统计时间'] = pd.to_datetime(ppi_df['统计时间'])
            ppi_last = ppi_df.sort_values('统计时间', ascending=False).iloc[0]
            ppi_val = float(ppi_last['当月同比'])
        except Exception as e:
            logger.error(f"Error fetching CPI/PPI: {e}")
            cpi_val = 0.0
            ppi_val = 0.0
            cpi_date = ""

        # 4. GDP (Quarterly)
        try:
            gdp_df = ak.macro_china_gdp()
            gdp_last = gdp_df.iloc[0]
            gdp_val = float(gdp_last['国内生产总值同比增长'])
            gdp_q = gdp_last['季度']
        except Exception as e:
            gdp_val = 0.0
            gdp_q = ""

        return {
            "money_supply": money_data,
            "pmi": pmi_data,
            "cpi": {"value": cpi_val, "date": cpi_date},
            "ppi": {"value": ppi_val},
            "gdp": {"value": gdp_val, "quarter": gdp_q}
        }
        
    except Exception as e:
        logger.error(f"Macro API Error: {e}")
        # Return empty structure rather than 500
        return {
            "money_supply": [],
            "pmi": [],
            "cpi": {"value": 0},
            "ppi": {"value": 0},
            "gdp": {"value": 0}
        }
