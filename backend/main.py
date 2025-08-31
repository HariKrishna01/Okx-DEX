import os
import json
import requests
import asyncio
import random
from dotenv import load_dotenv
from okx import Account, Trade
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# ----------------------------
# Load API Keys
# ----------------------------
load_dotenv()
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
PASSPHRASE = os.getenv("PASSPHRASE")

# ----------------------------
# Initialize OKX APIs
# ----------------------------
accountAPI = Account.AccountAPI(API_KEY, SECRET_KEY, PASSPHRASE, False, "1")  # False = sandbox
tradeAPI = Trade.TradeAPI(API_KEY, SECRET_KEY, PASSPHRASE, False, "1")

# ----------------------------
# Initialize FastAPI
# ----------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Helper: Get account balance
# ----------------------------
def get_balance(ccy="USDT"):
    balances = accountAPI.get_account_balance()
    for asset in balances["data"][0]["details"]:
        if asset["ccy"] == ccy:
            return float(asset["cashBal"])
    return 0.0

# ----------------------------
# Helper: Get best bid & ask
# ----------------------------
def get_best_prices(symbol="BTC-USDT"):
    url = f"https://www.okx.com/api/v5/market/books?instId={symbol}&sz=5"
    resp = requests.get(url).json()
    if resp["code"] != "0":
        raise Exception(f"Error fetching order book: {resp}")
    best_bid = float(resp["data"][0]["bids"][0][0])
    best_ask = float(resp["data"][0]["asks"][0][0])
    return best_bid, best_ask

# ----------------------------
# Helper: Calculate slippage
# ----------------------------
def calculate_slippage(expected_price, executed_price):
    return ((executed_price - expected_price) / expected_price) * 100

# ----------------------------
# TWAP Logic with WebSocket updates (Dynamic Slippage)
# ----------------------------
async def run_twap_ws(ws: WebSocket, instId: str, percent: float, slices: int, interval: int):
    cancelled = False

    async def listen_cancel():
        nonlocal cancelled
        while not cancelled:
            try:
                data = await ws.receive_json()
                if data.get("action") == "cancel":
                    cancelled = True
                    await ws.send_text(json.dumps({
                        "status": "cancelled",
                        "message": "TWAP cancelled by user"
                    }))
                    break
            except:
                break

    listener_task = asyncio.create_task(listen_cancel())

    await ws.send_text(json.dumps({
        "status": "start",
        "message": f"TWAP started for {instId}: {percent}% of balance in {slices} slices"
    }))

    for i in range(1, slices + 1):
        if cancelled:
            break

        balance = get_balance("USDT")
        total_usdt = balance * (percent / 100)
        slice_usdt = total_usdt / (slices - i + 1)

        best_bid, best_ask = get_best_prices(instId)
        price = (best_bid + best_ask) / 2
        size = slice_usdt / price

        # Place limit order (simulate execution)
        order_resp = tradeAPI.place_order(
            instId=instId,
            tdMode="cash",
            side="buy",
            ordType="limit",
            px=str(round(price, 2)),
            sz=str(round(size, 6))
        )

        await ws.send_text(json.dumps({
            "status": "slice_info",
            "slice": i,
            "total_slices": slices,
            "slice_size": round(size, 6),
            "price": round(price, 2)
        }))

        filled = 0.0
        step = 0.25 * size
        while filled < size and not cancelled:
            filled += step
            if filled > size:
                filled = size

            # Simulate executed price with random tiny slippage per partial fill
            executed_price = price * (1 + random.uniform(-0.001, 0.001))  # ±0.1%
            slippage = calculate_slippage(price, executed_price)

            await ws.send_text(json.dumps({
                "status": "partial_fill",
                "slice": i,
                "total_slices": slices,
                "price": round(price, 2),
                "size": round(filled, 6),
                "executed_price": round(executed_price, 2),
                "slippage_percent": round(slippage, 4)
            }))

            await asyncio.sleep(interval / 4)

    if not listener_task.done():
        listener_task.cancel()

    if not cancelled:
        await ws.send_text(json.dumps({
            "status": "completed",
            "message": "TWAP completed successfully!"
        }))

    await ws.close()

# ----------------------------
# WebSocket Endpoint
# ----------------------------
@app.websocket("/ws-twap")
async def websocket_twap(ws: WebSocket):
    await ws.accept()
    try:
        data = await ws.receive_json()
        instId = data.get("instId", "BTC-USDT")
        percent = float(data.get("percent", 10))
        slices = int(data.get("slices", 5))
        interval = int(data.get("interval", 30))
        await run_twap_ws(ws, instId, percent, slices, interval)
    except Exception as e:
        await ws.send_text(json.dumps({"status": "error", "message": str(e)}))
        await ws.close()

# ----------------------------
# REST test endpoint
# ----------------------------
@app.get("/")
def index():
    return {"status": "FastAPI TWAP server running"}
