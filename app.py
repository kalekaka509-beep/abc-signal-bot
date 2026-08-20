from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)

def find_swings(df):
    df['SwingHigh'] = df['High'][(df['High'].shift(1) < df['High']) & (df['High'].shift(-1) < df['High'])]
    df['SwingLow'] = df['Low'][(df['Low'].shift(1) > df['Low']) & (df['Low'].shift(-1) > df['Low'])]
    return df

def fib_level(A, B, level):
    return A + (B - A) * level

def calculate_signal(df):
    df = find_swings(df)
    highs = df.dropna(subset=['SwingHigh']).tail(5)
    lows = df.dropna(subset=['SwingLow']).tail(5)
    points = pd.concat([highs[['SwingHigh','Volume']], lows[['SwingLow','Volume']]]).sort_index().tail(4)

    if len(points) < 3:
        return {"error": "Not enough swing points found"}

    p = points.values
    A, B, C = p[-3][0], p[-2][0], p[-1][0]
    volA, volB, volC = p[-3][1], p[-2][1], p[-1][1]

    target = (B * C) / A

    fib_382 = fib_level(A, B, 0.382)
    fib_618 = fib_level(A, B, 0.618)
    fib_ok = fib_382 <= C <= fib_618

    avg_vol = (volA + volB) / 2
    vol_ok = volC < avg_vol * 0.7

    signal = "WAIT"
    reason = []
    if B > A and C < B and fib_ok and vol_ok:
        signal = "BUY"
        support = C * 0.99
        resistance = B
        reason = ["Bullish ABC", "C in Fib 38-61%", "Low Volume Pullback"]
    elif B < A and C > B and fib_ok and vol_ok:
        signal = "SELL"
        support = B
        resistance = C * 1.01
        reason = ["Bearish ABC", "C in Fib 38-61%", "Low Volume Pullback"]
    else:
        support = resistance = 0
        if not fib_ok: reason.append("C not in Fib Zone")
        if not vol_ok: reason.append("Volume too high")

    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "A": round(A,4), "B": round(B,4), "C": round(C,4),
        "Target": round(target,4), "Support": round(support,4),
        "Resistance": round(resistance,4), "Signal": signal,
        "Fib_Zone": f"{round(fib_382,4)} - {round(fib_618,4)}",
        "Reasons": reason
    }

@app.route("/", methods=["GET","POST"])
def home():
    result = None
    if request.method == "POST":
        symbol = request.form["symbol"]
        timeframe = request.form["timeframe"]
        try:
            data = yf.download(tickers=symbol, period="6mo", interval=timeframe, progress=False)
            result = calculate_signal(data)
            result["symbol"] = symbol
            result["timeframe"] = timeframe
        except:
            result = {"error": "Data fetch failed. Try 1h or 4h timeframe"}

    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
