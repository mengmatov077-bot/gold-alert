"""
gold_alert.py

Checks gold for an EMA9/EMA21 crossover and posts a message to Slack
if one just happened. Meant to be run automatically every few minutes
by GitHub Actions, so nothing needs to stay on on your phone or a PC.

Price comes from Yahoo Finance (gold futures, ticker GC=F) — not
directly from AMarkets — so it can differ slightly from your broker's
exact quote. Treat this as an alert to go check MT5, not an exact
execution price.

This is a placeholder rule (EMA9/EMA21 cross). Once you've tested and
trust a real entry rule, replace the logic inside check_crossover().
"""

import os
import sys
import requests
import yfinance as yf

TICKER = "GC=F"    # COMEX gold futures — close proxy for XAUUSD
INTERVAL = "5m"
LOOKBACK = "5d"     # enough 5-minute bars to compute EMA21 cleanly
FAST = 9
SLOW = 21


def get_webhook_url():
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("SLACK_WEBHOOK_URL secret is not set in the repo.")
        sys.exit(1)
    return url


def fetch_prices():
    data = yf.download(TICKER, interval=INTERVAL, period=LOOKBACK, progress=False)
    if isinstance(data.columns, __import__("pandas").MultiIndex):
        data.columns = data.columns.get_level_values(0)
    if data.empty or len(data) < SLOW + 2:
        print("Not enough data returned yet — will try again next run.")
        sys.exit(0)
    return data


def check_crossover(data):
    data["EMA_fast"] = data["Close"].ewm(span=FAST, adjust=False).mean()
    data["EMA_slow"] = data["Close"].ewm(span=SLOW, adjust=False).mean()

    last = data.iloc[-1]
    prev = data.iloc[-2]

    cross_up = prev["EMA_fast"] <= prev["EMA_slow"] and last["EMA_fast"] > last["EMA_slow"]
    cross_down = prev["EMA_fast"] >= prev["EMA_slow"] and last["EMA_fast"] < last["EMA_slow"]

    return cross_up, cross_down, float(last["Close"])


def send_slack(webhook_url, text):
    resp = requests.post(webhook_url, json={"text": text}, timeout=10)
    print("Slack response:", resp.status_code, resp.text)


def main():
    webhook_url = get_webhook_url()
    data = fetch_prices()
    cross_up, cross_down, price = check_crossover(data)

    print(f"Latest gold price: {price:.2f} | cross_up={cross_up} cross_down={cross_down}")

    if cross_up:
        send_slack(webhook_url, f"📈 Gold: EMA{FAST} crossed above EMA{SLOW} — price ~{price:.2f}")
    elif cross_down:
        send_slack(webhook_url, f"📉 Gold: EMA{FAST} crossed below EMA{SLOW} — price ~{price:.2f}")
    else:
        print("No crossover this run — staying quiet.")


if __name__ == "__main__":
    main()
