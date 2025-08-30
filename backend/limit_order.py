import os
import json
from time import time
from dotenv import load_dotenv
from okx import Account, Trade

# ----------------------
# Load API keys from .env
# ----------------------
load_dotenv()
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
PASSPHRASE = os.getenv("PASSPHRASE")

# ----------------------
# Initialize OKX APIs
# ----------------------
# False = sandbox, "1" = API key version
accountAPI = Account.AccountAPI(API_KEY, SECRET_KEY, PASSPHRASE, False, "1")
tradeAPI = Trade.TradeAPI(API_KEY, SECRET_KEY, PASSPHRASE, False, "1")

# ----------------------
# 1️⃣ Get Account Balances
# ----------------------
print("Fetching account balances...")
balances = accountAPI.get_account_balance()
print(json.dumps(balances, indent=4))

# ----------------------
# 2️⃣ Get BTC-USDT Order Book (Public)
# ----------------------
print("\nFetching BTC-USDT order book...")
import requests

orderbook_url = "https://www.okx.com/api/v5/market/books?instId=BTC-USDT&sz=5"  # top 5 bids/asks
response = requests.get(orderbook_url)
orderbook = response.json()
print(json.dumps(orderbook, indent=4))

# ----------------------
# 3️⃣ Place Limit Buy Order
# ----------------------
print("\nPlacing limit buy order...")

symbol = "BTC-USDT"
order_data = tradeAPI.place_order(
    instId=symbol,        # Trading pair
    tdMode="cash",   # Spot trading
    side="buy",           # buy or sell
    ordType="limit",      # Limit order
    px="25000",           # Price per BTC
    sz="0.001"            # Quantity to buy
)

print("\n📦 Order Response:")
print(json.dumps(order_data, indent=4))
