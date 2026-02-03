from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import random

router = APIRouter()

class TdxData(BaseModel):
    code: str
    price: float
    vol: float

@router.post("/calculate")
async def calculate_signal(data: TdxData):
    """
    Receives real-time data from Tongdaxin (TDX) via C++ DLL Bridge.
    Returns a signal: 1.0 (Buy), -1.0 (Sell), 0.0 (Hold).
    """
    # Log the incoming data (for debugging)
    print(f"[TDX Bridge] Received: Code={data.code}, Price={data.price}, Vol={data.vol}")
    
    # Placeholder Logic:
    # In a real app, this would query the Quant Engine / AI Model
    # Here we just implement a simple dummy logic
    
    signal = 0.0
    
    # Example: Simple price threshold or random for demo
    # If price ends with .00, signal buy (just to see it working)
    if int(data.price * 100) % 100 == 0:
        signal = 1.0
    elif int(data.price * 100) % 50 == 0:
        signal = -1.0
        
    return signal
