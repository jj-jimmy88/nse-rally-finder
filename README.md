# NSE Small-Cap Rally Finder

Daily, point-in-time application of two backtested rules to NSE stocks that pass the hygiene screen
(P/E < 50, market cap > ₹1,000 cr, annual profit growth > 20%) on the day.

* **R-A** — close ≥ 97% of 52-week high, ≥ 3× 52-week low, mcap < ₹2,000 cr, open gap < 2%, Apr–Dec
* **PB** — promoter open-market buy in last 90 days, close ≥ 90% of 52-week high, +10% in 20 days and +20% in 60, mcap < ₹3,000 cr

Execution: buy next open, −10% stop on the intraday low, hold 40 trading days, one signal per stock per 56 days.
Backtest (2023–26, out of sample): ~27 signals/yr, 20% reach +50%, avg +8% per trade with the stop.

## How it runs
* `daily.yml` — every trading day 16:50 IST: `update_prices.py` (Yahoo) → `update_insider.py` (NSE, best effort) → `engine.py` → `build_site.py` → commit → optional email.
* `fundamentals.yml` — 1st & 16th of the month: `refresh_fundamentals.py` (screener.in).
* Dashboard: `index.html` (GitHub Pages). Machine-readable: `data/latest.json` (today's new signals), `data/signals.json` (all live signals with forward tracking).

Email: set repo secrets `GMAIL_USER` and `GMAIL_APP_PASSWORD` (a Gmail app password) to have the workflow email new signals to jj.jimmy88@gmail.com.
