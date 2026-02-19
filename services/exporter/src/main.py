import time
import hmac
import hashlib
import base64
import uuid
import os
import json
import asyncio
import logging
from typing import Dict, List
import httpx
from prometheus_client import Gauge, start_http_server

# --- メトリクス定義 ---
# テストコード (tests/test_exporter.py) が import している名前と一致させる
POWER_WATT = Gauge(
    "switchbot_power_watts",
    "Current power usage in Watts",
    ["room", "shelf", "device", "device_name", "device_id", "parent_id"],
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

        # API制限の更新（copilot-instructions.md 準拠）
        remaining = resp.headers.get("x-ratelimit-remaining")
        if remaining is not None:
            API_REMAINING.set(int(remaining))
            if int(remaining) <= 100:
                logging.warning(f"API rate limit low: {remaining} calls remaining")
        else:
            logging.warning(
                f"Device {device_id}: x-ratelimit-remaining header not found"
            )

        resp.raise_for_status()
        data = resp.json()

        if data.get("statusCode") == 100:
            # 重要：SwitchBotプラグミニでは 'weight' が消費電力(W)を指す
            wattage = data["body"].get("weight", 0)

            POWER_WATT.labels(
                room=device["room"],
                shelf=device["shelf"],
                device=device["device"],
                device_name=device["name"],
                device_id=device_id,
                parent_id=device.get("parent_id", "none"),
            ).set(wattage)

            DEVICE_UP.labels(device_id=device_id).set(1)
            logging.info(f"Device {device_id}: power={wattage}W, remaining={remaining}")
        else:
            raise ValueError(f"API Error: {data.get('message')}")

    except Exception as e:
        logging.error(f"Device {device_id} fetch failed: {e}")
        # 失敗時は stale (古い値が残るの) を防ぐためにメトリクスを削除
        DEVICE_UP.labels(device_id=device_id).set(0)
        try:
            POWER_WATT.remove(
                device["room"],
                device["shelf"],
                device["device"],
                device["name"],
                device_id,
                device.get("parent_id", "none"),
            )
        except KeyError:
            pass  # すでに存在しない場合は無視


# --- 設定ロード機能 ---
def load_device_config(config_path: str = "devices.json") -> List[Dict[str, str]]:
    """
    デバイス設定ファイルを読み込む
    """
    # 設定ファイルが存在しない場合はサンプルデバイスを返す
    if not os.path.exists(config_path):
        logging.warning(f"Config file {config_path} not found. Using sample config.")
        return [
            {
                "id": "V2E012345678",
                "name": "main_tap",
                "device": "multi-tap-a",
                "room": "work",
                "shelf": "rack_1",
                "parent_id": "none",
            },
            {
                "id": "V2E987654321",
                "name": "server",
                "device": "pc",
                "room": "work",
                "shelf": "rack_1",
                "parent_id": "V2E012345678",
            },
        ]

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- メインアプリケーション ---
async def collect_metrics(
    devices: List[Dict[str, str]],
) -> None:
    """
    全デバイスのメトリクス収集を実行
    """
    token = (os.getenv("SWITCHBOT_TOKEN") or "").strip()
    secret = (os.getenv("SWITCHBOT_SECRET") or "").strip()

    if not token or not secret:
        raise ValueError("SWITCHBOT_TOKEN and SWITCHBOT_SECRET must be set")

    logging.info("Collecting metrics via SwitchBot API")
    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_device_status(client, device, token, secret) for device in devices
        ]
        await asyncio.gather(*tasks)


async def main_loop() -> None:
    """
    メインアプリケーションループ
    """
    # 環境変数の読み込み
    metrics_port = int(os.getenv("METRICS_PORT", "8000"))
    collection_interval = int(os.getenv("COLLECTION_INTERVAL", "60"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    config_path = os.getenv("DEVICE_CONFIG_PATH", "devices.json")

    # ロギング設定
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # デバイス設定の読み込み
    devices = load_device_config(config_path)
    logging.info(f"Loaded {len(devices)} devices from config")

    # Prometheusメトリクスサーバーの開始
    start_http_server(metrics_port)
    logging.info(f"Prometheus metrics server started on port {metrics_port}")

    logging.info("✅ REAL API MODE - Using actual SwitchBot API")

    # メインループ
    while True:
        try:
            await collect_metrics(devices)
            logging.info(
                f"Metrics collection completed. Next run in {collection_interval}s"
            )
        except Exception as e:
            logging.error(f"Error in metrics collection: {e}")

        await asyncio.sleep(collection_interval)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Application stopped by user")
