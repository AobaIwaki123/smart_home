"""
SwitchBot デバイス電力取得スクリプト

使い方:
    cd smart_home
    # 全デバイス（devices.json から）
    python services/exporter/scripts/get_device_power.py

    # デバイスIDを直接指定
    python services/exporter/scripts/get_device_power.py 588C81B65FDA 9888E0C67E5E

出力例:
    ─── Rate Limit ────────────────────────────
    x-ratelimit-limit     : 10000
    x-ratelimit-remaining : 9987
    x-ratelimit-reset     : 1708473600000  (2026-02-21 09:00:00 JST)

    ─── Device Results ─────────────────────────
    Device ID        : 588C81B65FDA
    Status Code      : 100
    weight (W)       : 22.6
    ...
"""

import asyncio
import json
import os
import sys
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from dotenv import load_dotenv
from src.main import generate_sign

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
# スクリプトをプロジェクトルートから実行した場合にも .env を読む
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))


def format_reset_time(reset_ms: str) -> str:
    try:
        ts = int(reset_ms) / 1000
        dt = datetime.datetime.fromtimestamp(
            ts, tz=datetime.timezone(datetime.timedelta(hours=9))
        )
        return f"{reset_ms}  ({dt.strftime('%Y-%m-%d %H:%M:%S JST')})"
    except (ValueError, TypeError):
        return reset_ms


async def fetch_status(
    client: httpx.AsyncClient, device_id: str, token: str, secret: str
) -> None:
    sign, t, nonce = generate_sign(token, secret)
    headers = {
        "Authorization": token,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json; charset=utf8",
    }

    url = f"https://api.switch-bot.com/v1.1/devices/{device_id}/status"
    resp = await client.get(url, headers=headers, timeout=10.0)

    # レート制限ヘッダー表示（最初のデバイスのみ表示させるため呼び出し元で制御）
    rate_info = {
        "limit": resp.headers.get("x-ratelimit-limit"),
        "remaining": resp.headers.get("x-ratelimit-remaining"),
        "reset": resp.headers.get("x-ratelimit-reset"),
    }

    print(f"\n{'─' * 20} Device: {device_id} {'─' * 20}")
    print(f"  HTTP Status      : {resp.status_code}")

    print(f"\n  --- Raw Headers ---")
    for k, v in resp.headers.items():
        print(f"  {k}: {v}")

    print(f"\n  --- Rate Limit Headers ---")
    print(f"  x-ratelimit-limit     : {rate_info['limit'] or '(ヘッダーなし)'}")
    print(f"  x-ratelimit-remaining : {rate_info['remaining'] or '(ヘッダーなし)'}")
    print(
        f"  x-ratelimit-reset     : {format_reset_time(rate_info['reset']) if rate_info['reset'] else '(ヘッダーなし)'}"
    )

    resp.raise_for_status()
    data = resp.json()

    status_code = data.get("statusCode")
    body = data.get("body", {})

    print(f"\n  --- Raw Response ---")
    print(f"  {resp.text}")

    print(f"\n  --- Parsed Fields ---")
    print(f"  statusCode       : {status_code}")
    print(f"  message          : {data.get('message')}")
    if body:
        print(f"  body:")
        for k, v in body.items():
            marker = "  ← 電力(W)" if k == "weight" else ""
            print(f"    {k:<24}: {v}{marker}")
    else:
        print(f"  body             : (空)")

    return rate_info


async def main() -> None:
    token = os.getenv("SWITCHBOT_TOKEN", "").strip()
    secret = os.getenv("SWITCHBOT_SECRET", "").strip()

    if not token or not secret:
        print("ERROR: SWITCHBOT_TOKEN / SWITCHBOT_SECRET が未設定です")
        print("  .env ファイルを確認するか、環境変数をエクスポートしてください")
        sys.exit(1)

    # 引数指定 or devices.json から読み込む
    if len(sys.argv) > 1:
        device_ids = sys.argv[1:]
    else:
        config_path = os.path.join(os.path.dirname(__file__), "..", "devices.json")
        if not os.path.exists(config_path):
            print(
                "ERROR: devices.json が見つかりません。デバイス ID を引数で指定してください"
            )
            sys.exit(1)
        with open(config_path, encoding="utf-8") as f:
            devices = json.load(f)
        device_ids = [d["id"] for d in devices]
        print(
            f"devices.json から {len(device_ids)} デバイスを読み込みました: {device_ids}"
        )

    print(f"\nSwitchBot API から電力情報を取得します...")

    async with httpx.AsyncClient() as client:
        for device_id in device_ids:
            try:
                await fetch_status(client, device_id, token, secret)
            except httpx.HTTPStatusError as e:
                print(f"\n  [ERROR] HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                print(f"\n  [ERROR] {type(e).__name__}: {e}")

    print(f"\n{'─' * 50}")
    print("完了")


if __name__ == "__main__":
    asyncio.run(main())
