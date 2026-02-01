# 🤖 Dual Trading Guide: Spot vs Futures

## **Overview**
Your bot can now trade on both **Spot** and **Futures** markets simultaneously, with intelligent market selection based on signal characteristics and market conditions.

## **🎯 Market Selection Logic**

### **When to Trade SPOT** 💰
- **High Confidence Signals** (score ≥ 0.75)
- **Low Volatility** (≤ 10%)
- **Long-term Timeframes** (≥ 4h)
- **Capital Preservation** trades
- **No Leverage Needed**

**Example**: BTC/USDT signal with 0.85 score, 8% volatility, 4h timeframe → **SPOT**

### **When to Trade FUTURES** ⚡
- **Medium-High Confidence** (score ≥ 0.65)
- **Moderate-High Volatility** (≥ 5%)
- **Short-Medium Timeframes** (≥ 1h)
- **Speculative Trades**
- **Leverage Required**

**Example**: ETH/USDT signal with 0.70 score, 12% volatility, 1h timeframe → **FUTURES**

## **📊 Decision Matrix**

| Signal Score | Volatility | Timeframe | Recommended Market |
|-------------|------------|-----------|-------------------|
| ≥ 0.8       | ≤ 8%       | ≥ 4h      | **SPOT**          |
| ≥ 0.75      | ≤ 10%      | ≥ 4h      | **SPOT**          |
| ≥ 0.7       | ≥ 5%       | ≥ 1h      | **FUTURES**       |
| ≥ 0.65      | ≥ 5%       | ≥ 1h      | **FUTURES**       |
| < 0.65      | Any        | Any       | **REJECT**        |

## **⚙️ Configuration**

### **Environment Variables**
```bash
# Enable/disable markets
BOT_ENABLE_SPOT_TRADING=true
BOT_ENABLE_FUTURES_TRADING=true
BOT_DEFAULT_TRADING_TYPE=auto

# Spot trading criteria
BOT_SPOT_TRADING_CRITERIA={"min_signal_score": 0.75, "max_volatility": 0.10, "min_timeframe": "4h", "max_leverage": 1.0}

# Futures trading criteria  
BOT_FUTURES_TRADING_CRITERIA={"min_signal_score": 0.65, "min_volatility": 0.05, "min_timeframe": "1h", "max_leverage": 3.0}
```

### **Risk Management**
- **Spot Trading**: Max 50% of balance per position (no leverage)
- **Futures Trading**: Max 30% of balance per position (with leverage)
- **Combined**: Max 5 concurrent positions across both markets

## **🚀 Usage Examples**

### **Example 1: High Confidence Signal**
```json
{
  "symbol": "BTC/USDT",
  "signal_score": 0.82,
  "volatility": 0.07,
  "timeframe": "4h",
  "direction": "LONG"
}
```
**Result**: → **SPOT Trading** (High confidence + Low volatility)

### **Example 2: Medium Confidence Signal**
```json
{
  "symbol": "ETH/USDT", 
  "signal_score": 0.68,
  "volatility": 0.12,
  "timeframe": "2h",
  "direction": "SHORT"
}
```
**Result**: → **FUTURES Trading** (Medium confidence + Moderate volatility)

### **Example 3: Low Confidence Signal**
```json
{
  "symbol": "ADA/USDT",
  "signal_score": 0.60,
  "volatility": 0.15,
  "timeframe": "1h",
  "direction": "LONG"
}
```
**Result**: → **REJECTED** (Below minimum criteria)

## **📈 Benefits of Dual Trading**

### **Risk Diversification**
- Spread risk across different market types
- Reduce correlation between positions
- Better capital allocation

### **Opportunity Capture**
- Spot for long-term trends
- Futures for short-term opportunities
- Leverage when appropriate

### **Flexibility**
- Adapt to different market conditions
- Optimize for signal characteristics
- Balance risk vs reward

## **🛡️ Safety Features**

### **Automatic Market Selection**
- No manual intervention required
- Based on objective criteria
- Prevents inappropriate market usage

### **Risk Controls**
- Separate position limits per market
- Appropriate leverage usage
- Market-specific stop losses

### **Monitoring**
- Track performance per market type
- Separate P&L reporting
- Market-specific analytics

## **🔧 Implementation**

### **Using the Dual Executor**
```python
from bot.execution.dual_executor import DualTradingExecutor

# Initialize dual executor
executor = DualTradingExecutor(test_mode=True)

# Execute signal (automatic market selection)
result = await executor.execute_signal(signal)

# Check which market was used
if result['success']:
    market = result['market']  # 'spot' or 'futures'
    print(f"Trade executed on {market.upper()} market")
```

### **Database Schema**
```sql
-- Market type tracking
ALTER TABLE paper_positions 
ADD COLUMN market_type VARCHAR(20) DEFAULT 'futures';

-- Query by market type
SELECT * FROM paper_positions 
WHERE market_type = 'spot' AND is_open = true;
```

## **📊 Performance Tracking**

### **Separate Metrics**
- Spot P&L vs Futures P&L
- Win rate by market type
- Average position duration
- Risk-adjusted returns

### **Dashboard Integration**
- Market type filters
- Performance comparison
- Risk metrics per market

## **🎯 Best Practices**

1. **Start Conservative**: Begin with lower leverage and higher signal thresholds
2. **Monitor Performance**: Track which market performs better for your strategy
3. **Adjust Criteria**: Fine-tune market selection based on results
4. **Risk Management**: Never exceed position limits across both markets
5. **Testing**: Always test in paper trading mode first

## **🚨 Important Notes**

- **API Keys**: Ensure your Binance API has permissions for both spot and futures
- **Balance Management**: Maintain adequate balances in both spot and futures wallets
- **Liquidation Risk**: Futures positions with leverage can be liquidated
- **Market Hours**: Consider market hours and liquidity for both markets

---

**Your bot now has professional-grade dual market capability!** 🎉

