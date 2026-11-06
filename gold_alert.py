
import os
import sys
import requests
import yfinance as yf

TICKER = "GC=F"
INTERVAL = "5m"
LOOKBACK = "5d"

FAST = 9
SLOW = 21


def get_ntfy_topic():
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC secret is not set")
        sys.exit(1)
    return topic


def fetch_prices():
    data = yf.download(
        TICKER,
        period=LOOKBACK,
        interval=INTERVAL,
        progress=False
    )

    if data.empty or len(data) < SLOW + 2:
        print("Not enough price data")
        sys.exit(0)

    if isinstance(data.columns, __import__("pandas").MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data


def check_crossover(data):
    close = data["Close"].dropna()

    ema_fast = close.ewm(span=FAST, adjust=False).mean()
    ema_slow = close.ewm(span=SLOW, adjust=False).mean()

    cross_up = (
        ema_fast.iloc[-2] <= ema_slow.iloc[-2]
        and ema_fast.iloc[-1] > ema_slow.iloc[-1]
    )

    cross_down = (
        ema_fast.iloc[-2] >= ema_slow.iloc[-2]
        and ema_fast.iloc[-1] < ema_slow.iloc[-1]
    )

    return cross_up, cross_down, float(close.iloc[-1])


def send_ntfy(topic, message):
    response = requests.post(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        headers={
            "Title": "Gold Alert XAUUSD",
            "Priority": "high"
        },
        timeout=15
    )
    response.raise_for_status()
    print("ntfy response:", response.status_code)


def main():
    topic = get_ntfy_topic()
    send_ntfy(topic, "TEST: Gold Alert connected successfully!")
    data = fetch_prices()

    cross_up, cross_down, price = check_crossover(data)

    print(f"Gold price: {price:.2f}")

    if cross_up:
        send_ntfy(
            topic,
            f"BUY SIGNAL: EMA{FAST} crossed above EMA{SLOW}. Price: {price:.2f}"
        )

    elif cross_down:
        send_ntfy(
            topic,
            f"SELL SIGNAL: EMA{FAST} crossed below EMA{SLOW}. Price: {price:.2f}"
        )

    else:
        print("No crossover")


if __name__ == "__main__":
    main()

