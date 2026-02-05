---
name: stock-sell-decision
description: Comprehensive stock sell decision analysis using technical indicators for A-share stocks. Use when helping users decide whether to sell stocks through technical analysis. Supports quick analysis with Softmax-based probability scoring and deep technical analysis across 7 dimensions including MACD, moving averages, RSI, KDJ, volume analysis, divergence detection, and trend identification. Ideal for daily portfolio review, pre-trade decisions, and technical analysis learning.
---

# Stock Sell Decision

## Overview

This skill provides two complementary approaches for stock sell decision analysis:

1. **Quick Analysis** (`sell_analyzer.py`): Softmax-based fusion of 6 technical indicators to generate a sell probability score and actionable recommendation
2. **Deep Analysis** (`deep_analyzer.py`): Comprehensive 7-dimension technical analysis for detailed understanding

Both tools analyze A-share stocks using free data from AKShare API.

## Quick Start

Choose the appropriate tool based on your need:

### For Quick Decisions

```bash
python sell_analyzer.py
```

**When to use**: Need fast "sell/hold" recommendation with probability score

**What it provides**:
- Sell probability (0-100%)
- Risk level (safe/moderate/high/extreme)
- Actionable recommendation (hold/sell/reduce position)
- Technical indicator scores (0-10 for each of 6 indicators)

**Example workflow**:
1. Run script and input stock code (e.g., 600000)
2. Choose trading mode (conservative/standard/aggressive)
3. Get immediate sell probability and recommendation

### For Deep Analysis

```bash
python deep_analyzer.py
```

**When to use**: Need detailed technical analysis to understand WHY

**What it provides**: 7 analysis dimensions
1. Moving average system (MA crossovers, alignment, slope)
2. MACD analysis (10-day history, green/red bar duration)
3. Oscillation vs trend detection
4. Volume analysis (price-volume relationship)
5. Divergence detection (top/bottom divergence)
6. RSI & KDJ analysis (overbought/oversold)
7. Summary with risk signal count and recommendations

## Decision Workflow

```
User asks: "Should I sell stock XXXXX?"

   ↓
Quick Analysis (sell_analyzer.py)
   ↓
Sell Probability > 70%?
   ├─ YES → Deep Analysis (deep_analyzer.py)
   │         ↓
   │      Confirm sell signals
   │         ↓
   │      Execute sell decision
   │
   └─ NO → Continue holding
```

## Technical Indicators

### Quick Analysis Indicators

All 6 indicators scored 0-10 (higher = more risky):

| Indicator | Weight | Signals Tracked |
|-----------|--------|-----------------|
| MA Death Cross | 2.0 | MA5 crosses below MA20, price breaks below MA60 |
| MACD | 1.8 | DIF crosses below DEA, bars turn from red to green |
| RSI Overbought | 1.5 | RSI > 70, top divergence |
| KDJ | 1.3 | High death cross (K > 80), overbought |
| Bollinger Bands | 1.2 | Touching upper band, widening |
| Volume-Price | 1.6 | High-volume drop, price rise with shrinking volume |

**Scoring example**:
- MA death cross (fresh): +9 points
- MACD green bars: +5 points
- RSI > 70: +6 points
- Total weighted score determines sell probability via Softmax

### Deep Analysis Dimensions

#### 1. Moving Average System
- Multi-timeframe MA (5/20/60 days)
- Golden cross / Death cross detection
- MA alignment (bullish: price > MA5 > MA20 > MA60)
- MA slope analysis (flat = oscillation, up = uptrend, down = downtrend)

#### 2. MACD Analysis
- 10-day historical tracking
- Green bar duration (green > 5 days = downtrend confirmed)
- DIF/DEA crossover signals

#### 3. Oscillation vs Trend
- Price range analysis (60-day high/low)
- 20-day total change (< 10% = oscillation)
- Volatility analysis
- MA slope assessment
- **Signal counting**: Oscillation signals vs Trend signals to determine market state

#### 4. Volume Analysis
- Volume ratio (current / 20-day average)
- Price-volume relationship:
  - Price up + High volume = Healthy
  - Price up + Low volume = Divergence (caution)
  - Price down + High volume = Panic selling
  - Price down + Low volume = May not have bottomed

#### 5. Divergence Detection
- **Top divergence**: Price makes new high but MACD/RSI doesn't confirm (dangerous)
- **Bottom divergence**: Price makes new low but MACD/RSI doesn't confirm (opportunity)

#### 6. RSI & KDJ
- RSI levels: >80 (severely overbought), >70 (overbought), <20 (severely oversold), <30 (oversold)
- KDJ signals: High death cross (K > 80), low golden cross (K < 20)

#### 7. Summary
- Risk signal count (0-4)
- Position size recommendation
- Key price levels (support/resistance)

## Trading Modes

### Quick Analysis supports 3 modes via temperature parameter:

| Mode | Temperature | Sell Threshold | Best For |
|------|-------------|----------------|----------|
| Conservative | 0.5 | > 80% | Long-term investors, risk-averse |
| Standard | 1.0 | > 70% | Most investors |
| Aggressive | 1.5 | > 55% | Short-term traders, risk-tolerant |

Higher temperature = More sensitive to sell signals (lower threshold)

## Common Patterns

### Pattern 1: Oscillation with False Death Cross

**Example**: Stock 601988 (Bank of China)

```
Quick Analysis: Sell probability 2.9% (safe)
Deep Analysis:
  - Oscillation market (20-day change -1.6%)
  - MACD red bars (turned positive)
  - MA death cross is technical phenomenon in oscillation
  - Low price position (14.3% percentile of 60-day range)

→ Conclusion: Bottom oscillation, continue holding
```

**Lesson**: In oscillation markets, MA death crosses are often false signals. Confirm with:
- MACD direction (red bars = OK)
- Price position in range (low = OK)
- Overall trend (MA slope flat = oscillation)

### Pattern 2: Downtrend with Strong Sell Signals

**Example**: Stock 002555 (37 Interactive Entertainment)

```
Quick Analysis: Sell probability 100% (extreme risk)
Deep Analysis:
  - MACD green bars for 12 days (accelerating)
  - 20-day drop -8.46%
  - Green bars widening (-0.34 → -1.04)
  - Shrinking volume (no buyers)

→ Conclusion: Confirmed downtrend, reduce position
```

**Lesson**: MACD green bar duration is critical:
- Green 3-5 days = Normal correction
- Green > 5 days = Downtrend confirmed
- Green bars widening = Downward momentum increasing

### Pattern 3: High-Oscillation Market

**Example**: Stock 002624 (Perfect World)

```
Quick Analysis: Sell probability 100% (extreme risk)
Deep Analysis:
  - Oscillation market (3 oscillation signals)
  - Price at 78% percentile (near upper bound)
  - Range: 14.05 - 18.84, current 17.79
  - MA death cross = distribution at upper bound

→ Corrected View: Not crash, but taking profits at oscillation top
→ Strategy: Reduce position 30-50%, buy back at 16-16.5 support
```

**Lesson**: Oscillation markets require different strategy:
- Identify range (support/resistance)
- Buy low (0-30% percentile), sell high (70-100% percentile)
- Don't chase breakouts, don't panic sell at lows

## Important Limitations

1. **Data source**: AKShare (free), may have delays. Use after market close
2. **Technical indicator lag**: Indicators reflect past price action, not future events
3. **Black swan events**: Sudden news (policy changes, scandals) not captured
4. **Market context**: Always check overall market trend (Shanghai/Shenzhen indices)
5. **Fundamentals**: Technical analysis doesn't replace fundamental analysis

**Best practice**: Combine with:
- Overall market sentiment
- Sector trends
- Company fundamentals (earnings, valuation)
- Risk management (stop-loss, position sizing)

## Dependencies

Required Python packages:
```bash
pip install akshare numpy pandas
```

Data source: AKShare (free A-share data API)

## Stock Code Format

- Shanghai: 600xxx, 601xxx, 603xxx, 688xxx (STAR Market)
- Shenzhen: 000xxx, 001xxx, 002xxx, 300xxx (ChiNext)

Example: 600000 (SPDB), 000001 (PING AN), 300750 (NINJA)

## Resources

### scripts/

- **sell_analyzer.py**: Quick analysis tool with Softmax-based indicator fusion
  - Computes 6 technical indicators (MA, MACD, RSI, KDJ, Bollinger, Volume)
  - Applies weighted scoring and Softmax for probability
  - Supports 3 trading modes (conservative/standard/aggressive)

- **deep_analyzer.py**: Comprehensive 7-dimension technical analysis
  - Moving average system with crossover detection
  - MACD with 10-day history tracking
  - Oscillation vs trend classification
  - Volume-price relationship analysis
  - Divergence detection (top/bottom)
  - RSI & KDJ overbought/oversold analysis
  - Risk signal summary with actionable recommendations

Both scripts are production-ready and tested on real A-share stocks.

### references/

- **usage.md**: Complete user guide including:
  - Installation instructions
  - Usage examples for both tools
  - Comparison table (quick vs deep analysis)
  - Recommended workflows
  - 3 real-world case studies with detailed analysis
  - Trading mode explanations
  - FAQ section
  - Technical indicator learning resources

Load this reference when:
- User needs detailed usage instructions
- Clarifying which tool to use for specific scenarios
- Understanding differences between analysis modes
- Learning technical analysis concepts
