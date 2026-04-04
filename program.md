# autoresearch-trading

This is an experiment to have the LLM research and optimize a trading strategy for XAUUSD (Gold).

## Setup

1. **Symbol**: XAUUSD
2. **Timeframe**: M5 (5 minutes)
3. **Data**: Provided by `prepare.py` via MetaTrader 5.
4. **Metric**: `val_sharpe` (Annualized Sharpe Ratio).

## Experimentation

The training script `train.py` runs for a **fixed time budget of 5 minutes**. 

**What you CAN do:**
- Modify `train.py`. You can change the model architecture (MLP, Transformer, CNN, etc.), hyperparameters, optimizer, and the feature processing.
- The goal is to maximize **val_sharpe**.

**What you CANNOT do:**
- Modify `prepare.py`. It is read-only and handles the data loading and backtesting logic.
- Install new packages.

**The goal is simple: get the highest val_sharpe.** 

## Output format

Once the script finishes it prints a summary like this:

```
---
val_sharpe:       1.234567
training_seconds: 300.1
total_seconds:    310.5
peak_vram_mb:     1024.0
num_steps:        50000
num_params:       12345
depth:            3
```

## Logging results

Log to `results.tsv` (tab-separated).

Columns: `commit`, `val_sharpe`, `memory_gb`, `status`, `description`

## The experiment loop

LOOP FOREVER:

1. Tune `train.py` with a new trading model idea.
2. git commit
3. Run: `uv run train.py > run.log 2>&1`
4. Read results: `grep "^val_sharpe:\|^peak_vram_mb:" run.log`
5. Record in `results.tsv`.
6. Advance branch if `val_sharpe` improved (higher is better).
7. Revert if it didn't.

**NEVER STOP**: Continue researching until manually stopped.
