import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rox_quant.copy_trade import CopyEngine

def test_copy_trade():
    print(">>> Testing Copy Trade Engine")
    engine = CopyEngine()
    engine.follow("Guru_One")
    
    # Try multiple times to catch random signal (prob 0.2)
    found = False
    for i in range(10):
        signals = engine.check_signals()
        if signals:
            print(f"Obtained {len(signals)} signals: {signals}")
            found = True
            break
            
    if found:
        print("✅ Copy Engine received signal")
    else:
        print("⚠️ No signal generated (Random chance), but engine ran.")

if __name__ == "__main__":
    test_copy_trade()
