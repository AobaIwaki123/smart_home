import time
import hmac
import hashlib
import base64
import uuid
import asyncio
import os
import httpx
from prometheus_client import Gauge

# --- メトリクス定義 ---
# テストコード (tests/test_exporter.py) が import している名前と一致させる
POWER_WATT = Gauge(
    "switchbot_power_watts",
    "Current power usage in Watts",
    ["house", "room", "shelf", "device_name", "device_id"],
)

DEVICE_UP = Gauge(
    "switchbot_device_up", "Device availability (1: OK, 0: NG)", ["device_id"]
)

API_REMAINING = Gauge(
    "switchbot_api_requests_remaining", "Remaining API calls for the day"
)


# --- 署名生成ロジック ---
def generate_sign(token: str, secret: str):
    """SwitchBot API v1.1 の署名を生成する"""
    nonce = str(uuid.uuid4())
    t = str(int(time.time() * 1000))
    string_to_sign = f"{token}{t}{nonce}"
    sign = base64.b64encode(
        hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    ).upper()
    return str(sign, "utf-8"), t, nonce


# --- データ取得ロジック ---
async def fetch_device_status(
    client: httpx.AsyncClient, device: dict, token: str, secret: str
):
    """単一デバイスのステータスを取得し、メトリクスを更新する"""
    device_id = device["id"]
    sign, t, nonce = generate_sign(token, secret)

    headers = {
        "Authorization": token,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json; charset=utf8",
    }

    try:
        url = f"https://api.switch-bot.com/v1.1/devices/{device_id}/status"
        resp = await client.get(url, headers=headers, timeout=10.0)

        # API制限の更新
        remaining = resp.headers.get("x-ratelimit-remaining")
        if remaining:
            API_REMAINING.set(int(remaining))

        resp.raise_for_status()
        data = resp.json()

        if data.get("statusCode") == 100:
            # 重要：SwitchBotプラグミニでは 'weight' が消費電力(W)を指す
            wattage = data["body"].get("weight", 0)

            POWER_WATT.labels(
                house=device["house"],
                room=device["room"],
                shelf=device["shelf"],
                device_name=device["name"],
                device_id=device_id,
            ).set(wattage)

            DEVICE_UP.labels(device_id=device_id).set(1)
        else:
            raise ValueError(f"API Error: {data.get('message')}")

    except Exception as e:
        # 失敗時は stale (古い値が残るの) を防ぐためにメトリクスを削除
        DEVICE_UP.labels(device_id=device_id).set(0)
        try:
            POWER_WATT.remove(
                device["house"],
                device["room"],
                device["shelf"],
                device["name"],
                device_id,
            )
        except KeyError:
            pass  # すでに存在しない場合は無視
