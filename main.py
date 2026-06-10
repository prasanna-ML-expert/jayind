import os
import json
import requests
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# ====== CONFIG FROM GITHUB SECRETS ======
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WALLETS_JSON = os.getenv("MYLIST21")  # your secret name

RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
# Tokens to ignore (add more as needed)
EXCLUDED_TOKENS = {    
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrEdpN4HVEhVHgF4PnMiBxactAesQfymh",  # USDT
    "So11111111111111111111111111111111111111112",  # SOL (wrapped SOL)
    "HzwqbKZw8HxMN6bF2yFZNrht3c2iXXzpKcFu7uBEDKtr", #EURC

}
# ====== HELPERS ======

def get_lookup_window_seconds():
    now_local = datetime.now(ZoneInfo("America/Chicago"))
    hour = now_local.hour

    # If we're in quiet hours → skip execution entirely
    if hour >= 22 or hour < 6:
        return None

    # If just resumed at 6 AM → fetch overnight data
    if hour == 6:
        return 8 * 3600  # 8 hours (10PM → 6AM)

    # Normal hourly run
    return 3600
    
def send_telegram(msg):
    url = f"https://api.telegram.org/{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload, timeout=10)


def get_signatures(address, limit=10):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [address, {"limit": limit}]
    }
    res = requests.post(RPC_URL, json=payload, timeout=10)
    return res.json().get("result", [])


def get_transaction(sig):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
    }
    res = requests.post(RPC_URL, json=payload, timeout=15)
    return res.json().get("result")


def extract_token_transfers(tx, wallet):
    """
    Extract ALL token balance deltas (inner + outer)
    """
    results = []

    meta = tx.get("meta", {})
    pre = meta.get("preTokenBalances", [])
    post = meta.get("postTokenBalances", [])

    # build maps
    pre_map = {}
    post_map = {}

    for b in pre:
        owner = b.get("owner")
        mint = b.get("mint")
        amt = float(b["uiTokenAmount"]["uiAmount"] or 0)
        pre_map[(owner, mint)] = amt

    for b in post:
        owner = b.get("owner")
        mint = b.get("mint")
        amt = float(b["uiTokenAmount"]["uiAmount"] or 0)
        post_map[(owner, mint)] = amt

    keys = set(pre_map.keys()) | set(post_map.keys())

    for (owner, mint) in keys:
        if owner != wallet:
            continue

        pre_amt = pre_map.get((owner, mint), 0)
        post_amt = post_map.get((owner, mint), 0)
        delta = post_amt - pre_amt

        if abs(delta) > 0:
            results.append({
                "mint": mint,
                "amount": delta
            })

    return results


# ====== MAIN LOGIC ======
def run():
    window = get_lookup_window_seconds()
    if window is None:
        #print("Skipping due to quiet hours")
        exit(0)
        
    wallets = json.loads(WALLETS_JSON)
    now = datetime.now(timezone.utc)
    cutoff_time = now.timestamp() - window
    alerts = []

    for w in wallets:
        address = w["address"]

        signatures = get_signatures(address, limit=10)

        for sig_info in signatures:
            block_time = sig_info.get("blockTime")
            if not block_time:
                continue

            if block_time < cutoff_time:
                continue

            tx = get_transaction(sig_info["signature"])
            if not tx:
                continue

            transfers = extract_token_transfers(tx, address)

            for t in transfers:
                mint = t["mint"]
                amount = t["amount"]

                if mint in EXCLUDED_TOKENS:
                    continue

                # ignore pure SOL (no mint) and tiny noise
                if not mint or abs(amount) < 1e-6:
                    continue

                local_time = datetime.fromtimestamp(block_time, tz=ZoneInfo("America/Chicago"))

                alerts.append({
                    "wallet": address,
                    "mint": mint,
                    "amount": amount,
                    "time": local_time.strftime("%Y-%m-%d %H:%M:%S %Z")
                })
            time.sleep(0.2)

    # ====== SEND ALERT ONLY IF NEW TOKENS ======
    if alerts:
        msg = "<b>🚨 New Token Activity (Last 1h)</b>\n\n"

        for a in alerts:
            dex_url = f"https://dexscreener.com/solana/{a['mint']}"
            msg += (
                f"<b>Wallet:</b> {a['wallet']}\n"
                f"<b>Token:</b> <a href='{dex_url}'>{a['mint']}</a>\n"
                f"<b>Amount:</b> {a['amount']:.6f}\n"
                f"<b>Time:</b> {a['time']}\n"
                f"-------------------\n"
            )
        send_telegram(msg)


if __name__ == "__main__":
    run()
