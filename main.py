import os
import json
import requests
from datetime import datetime, timezone

# ====== CONFIG FROM GITHUB SECRETS ======
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WALLETS_JSON = os.getenv("MYLIST21")  # your secret name

RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# ====== HELPERS ======
def send_telegram(msg):
    url = f"https://api.telegram.org/{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
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
    wallets = json.loads(WALLETS_JSON)
    now = datetime.now(timezone.utc)
    one_hour_ago = now.timestamp() - 3600

    alerts = []

    for w in wallets:
        address = w["address"]

        signatures = get_signatures(address, limit=10)

        for sig_info in signatures:
            block_time = sig_info.get("blockTime")
            if not block_time:
                continue

            if block_time < one_hour_ago:
                continue  # only last 1 hour

            tx = get_transaction(sig_info["signature"])
            if not tx:
                continue

            transfers = extract_token_transfers(tx, address)

            for t in transfers:
                mint = t["mint"]
                amount = t["amount"]

                # ignore pure SOL (no mint) and tiny noise
                if not mint or abs(amount) < 1e-6:
                    continue

                time_str = datetime.fromtimestamp(block_time, tz=timezone.utc)

                alerts.append({
                    "wallet": address,
                    "mint": mint,
                    "amount": amount,
                    "time": time_str.strftime("%Y-%m-%d %H:%M:%S UTC")
                })

    # ====== SEND ALERT ONLY IF NEW TOKENS ======
    if alerts:
        msg = "<b>🚨 New Token Activity (Last 1h)</b>\n\n"

        for a in alerts:
            msg += (
                f"<b>Wallet:</b> {a['wallet']}\n"
                f"<b>Token:</b> {a['mint']}\n"
                f"<b>Amount:</b> {a['amount']:.6f}\n"
                f"<b>Time:</b> {a['time']}\n"
                f"-------------------\n"
            )

        send_telegram(msg)


if __name__ == "__main__":
    run()
