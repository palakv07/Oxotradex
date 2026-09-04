# Resetting Alpaca Paper Trading Account to $100,000

For the **Alpaca AI Trading Agents Hackathon**, submissions must be demonstrated on a clean paper trading account with an exact starting balance of **$100,000.00**.

Follow these simple steps to reset your Alpaca Paper Trading account:

---

### Method 1: Alpaca Web Dashboard (Fastest)

1. Log into your Alpaca account: [https://app.alpaca.markets](https://app.alpaca.markets).
2. Ensure you are on the **Paper Trading** dashboard (indicated by a purple/yellow "Paper" banner).
3. Navigate to **Account Settings** or **Overview**.
4. In the upper right corner of the Paper Overview page, locate the **"Reset Account"** or **"Reset Paper Account"** button.
5. In the confirmation dialog:
   - Enter starting cash amount: **$100,000.00**
   - Confirm reset.
6. All existing positions, orders, and historical PnL will be wiped clean, and your account equity will be restored to exactly **$100,000.00**.

---

### Method 2: Reset Local SQLite Agent State

Whenever you reset your Alpaca Paper Account, also reset the agent's local SQLite audit database so that local tracking matches broker equity:

```bash
# On Windows (PowerShell or CMD)
del alpaca_agent.db

# On Linux / macOS
rm alpaca_agent.db
```

When you next start the agent, it will automatically regenerate a fresh `alpaca_agent.db` schema and synchronize with your brand-new $100,000 paper balance.

---

### Method 3: Verification

Verify that your account has been properly reset by running:

```bash
python src/main.py --once --dry-run
```

You should see:
```text
[*] [INFO] Account Status: Equity: $100,000.00 | Cash: $100,000.00 | Daily PnL: $+0.00 (+0.00%)
[*] [INFO] No open spread positions to evaluate.
```
