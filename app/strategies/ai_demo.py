import random

# --- Qbot/Ptrade Style AI Strategy Demo ---
# This strategy demonstrates the structure used in professional quant platforms (Ptrade/Zipline).
# It mocks an AI model (e.g., XGBoost/Transformer) decision process.

def initialize(context):
    """
    Called once at the beginning of the backtest.
    Initialize parameters, load models, and set trading universe.
    """
    print("[AI Strategy] Initializing Qbot-style Engine...")
    
    # 1. Define Universe (Ptrade style)
    context.universe = ["600519.SH", "000001.SZ", "300750.SZ"]
    
    # 2. Load Pre-trained Model
    # In a real Qbot scenario, you would load a .pkl or .onnx file here.
    # context.model = joblib.load('my_ai_model.pkl')
    context.model_weights = {
        "trend_score": 0.6,
        "volatility_score": 0.3,
        "sentiment_score": 0.1
    }
    
    # 3. Set Execution Parameters
    context.holding_period = 0
    context.max_position_pct = 0.2  # Max 20% per stock

def handle_data(context, data):
    """
    Called every bar (minute/day).
    Core logic for Feature Engineering -> Inference -> Execution.
    """
    
    for code in context.universe:
        if code not in data:
            continue
            
        bar = data[code]
        close_price = bar['close']
        
        # --- Step 1: Feature Engineering (Online) ---
        # Calculate technical indicators on the fly
        ma_5 = close_price * (1 + random.uniform(-0.02, 0.02)) # Mock MA
        ma_20 = close_price * (1 + random.uniform(-0.05, 0.05)) # Mock MA
        
        # --- Step 2: AI Inference (Mock) ---
        # Input features into the model to get a prediction score (-1 to 1)
        # score = context.model.predict([ma_5, ma_20, ...])
        
        # Simulating model output:
        trend_signal = 1 if ma_5 > ma_20 else -1
        vol_signal = random.choice([-1, 0, 1])
        
        ai_score = (trend_signal * context.model_weights["trend_score"]) + \
                   (vol_signal * context.model_weights["volatility_score"])
        
        # Add some random noise (market uncertainty)
        ai_score += random.uniform(-0.1, 0.1)
        
        # --- Step 3: Execution Logic (Risk Management) ---
        current_position = context.portfolio["positions"].get(code, 0)
        
        # Buy Logic
        if ai_score > 0.4:
            target_value = context.portfolio["total_value"] * context.max_position_pct
            if current_position * close_price < target_value:
                # print(f"AI Signal [BUY] {code} Score:{ai_score:.2f} Price:{close_price}")
                context.order_target_value(code, target_value)
        
        # Sell Logic
        elif ai_score < -0.2:
            if current_position > 0:
                # print(f"AI Signal [SELL] {code} Score:{ai_score:.2f}")
                context.order_target(code, 0)
                
    context.holding_period += 1

