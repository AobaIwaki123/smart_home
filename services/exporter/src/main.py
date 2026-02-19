import time
import hmac
import hashlib
import base64
import uuid
import os
import json
import random
import asyncio
import logging
from typing import Dict, List, Any
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
                room=device["room"],
                shelf=device["shelf"],
                device=device["device"],
                device_name=device["name"],
                device_id=device_id,
                parent_id=device.get("parent_id", "none"),
            ).set(wattage)

            DEVICE_UP.labels(device_id=device_id).set(1)
        else:
            raise ValueError(f"API Error: {data.get('message')}")

    except Exception as e:
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


# --- モック機能 ---
def get_mock_switchbot_response(device_id: str) -> Dict[str, Any]:
    """
    SwitchBot API v1.1 のレスポンスをモック生成する
    80%の確率で待機電力(5-10W)、20%の確率で高負荷(100-300W)をシミュレート
    """
    is_high_load = random.random() > 0.8
    if is_high_load:
        wattage = random.uniform(100.0, 300.0)
    else:
        wattage = random.uniform(5.0, 10.0)

    return {
        "statusCode": 100,
        "body": {
            "deviceId": device_id,
            "deviceType": "Plug Mini (JP)",
            "hubDeviceId": "000000000000",
            "voltage": 100.0 + random.uniform(-1, 1),
            "weight": round(wattage, 2),  # パース対象の消費電力
            "electricCurrent": round(wattage / 100.0, 2),
            "onSignal": "mock_signal_on",
            "offSignal": "mock_signal_off",
        },
        "message": "success",
    }


async def fetch_device_status_mock(device: Dict[str, str]) -> None:
    """
    モック環境でのデバイスステータス取得
    実際のAPIは呼ばずにモックデータでメトリクスを更新
    """
    device_id = device["id"]

    try:
        # モックデータを生成
        data = get_mock_switchbot_response(device_id)

        # API制限をモック（高い値に設定）
        API_REMAINING.set(9999)

        if data.get("statusCode") == 100:
            wattage = data["body"].get("weight", 0)

            # sourceラベルを追加してモック環境であることを明示
            POWER_WATT.labels(
                room=device["room"],
                shelf=device["shelf"],
                device=device["device"],
                device_name=device["name"],
                device_id=device_id,
                parent_id=device.get("parent_id", "none"),
            ).set(wattage)

            DEVICE_UP.labels(device_id=device_id).set(1)

            logging.info(f"Mock data updated: {device_id} = {wattage}W")
        else:
            raise ValueError(f"Mock API Error: {data.get('message')}")

    except Exception as e:
        logging.error(f"Mock device {device_id} failed: {e}")
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
            pass


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
    devices: List[Dict[str, str]], use_mock: bool = False
) -> None:
    """
    全デバイスのメトリクス収集を実行
    """
    if use_mock:
        # モック環境
        logging.info("Using MOCK mode for data collection")
        tasks = [fetch_device_status_mock(device) for device in devices]
        await asyncio.gather(*tasks)
    else:
        # 実際のAPI環境
        token = os.getenv("SWITCHBOT_TOKEN")
        secret = os.getenv("SWITCHBOT_SECRET")

        if not token or not secret:
            raise ValueError("SWITCHBOT_TOKEN and SWITCHBOT_SECRET must be set")

        logging.info("Using REAL API for data collection")
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
    use_mock = os.getenv("USE_MOCK", "false").lower() == "true"
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

    if use_mock:
        logging.warning("⚠️ MOCK MODE ENABLED - Not using real SwitchBot API")
    else:
        logging.info("✅ REAL API MODE - Using actual SwitchBot API")

    # メインループ
    while True:
        try:
            await collect_metrics(devices, use_mock)
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
