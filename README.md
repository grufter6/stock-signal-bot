# stock-signal-bot

Runs on GitHub Actions (works even when your laptop is off). Once a day it
classifies a watchlist into "volatile" and "steady" buckets using historical
data from yfinance. Every 5 minutes during US market hours it checks live
Finnhub quotes against that classification and pushes a phone notification
via ntfy.sh when something crosses a threshold — it never places trades.

This is an informational screener, not financial advice, and not a
guarantee of anything — it flags moves worth looking at, you decide what to
do about them.

## One-time setup

1. **Finnhub API key** — sign up free at https://finnhub.io, copy the API
   key from your dashboard.
2. **ntfy topic** — pick (or let me generate) a random, hard-to-guess topic
   name, e.g. `stockbot-x7k2p9`. Install the [ntfy app](https://ntfy.sh) on
   your phone and subscribe to that exact topic name. Anyone who knows the
   topic name can read it, so keep it private.
3. Add both as GitHub Actions secrets on this repo (do this from your own
   terminal so the values never pass through chat):
   ```
   gh secret set FINNHUB_API_KEY --repo <you>/stock-signal-bot
   gh secret set NTFY_TOPIC --repo <you>/stock-signal-bot
   ```
   Each prompts you to paste the value.
4. Trigger the daily scan once manually so `state/classification.json` is
   populated (otherwise the first automatic run is tomorrow morning):
   ```
   gh workflow run daily-scan.yml --repo <you>/stock-signal-bot
   ```

## Notes / limits

- GitHub Actions scheduled workflows are best-effort — they can be delayed
  several minutes under high platform load, and GitHub **auto-disables**
  scheduled workflows after 60 days with no repo activity (any push
  re-enables them — the daily-scan commits count, so this should stay
  alive on its own).
- Finnhub's free tier doesn't include historical candles, which is why
  historical/technical calculations use yfinance (same free, unofficial
  Yahoo Finance source your stock-trend-dashboard already uses) while
  Finnhub supplies the live quotes.
- The watchlist (`watchlist.py`) is a fixed curated list, not a scan of the
  entire market — free-tier data sources don't support bulk-screening
  thousands of tickers on a 5-minute cadence. Edit that file to change
  which symbols are considered.
