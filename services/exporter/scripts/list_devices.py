"""
SwitchBot デバイス一覧取得スクリプト

使い方:
    cd services/exporter
    export SWITCHBOT_TOKEN="your_token"
    export SWITCHBOT_SECRET="your_secret"
    python scripts/list_devices.py

  または .env ファイルに書いておく場合:
    python scripts/list_devices.py

出力例:
    [Physical Devices]
    No.  deviceId               deviceType                name
    ---  ---------------------  ------------------------  ----
    1    AABBCCDDEEFF           Plug Mini (JP)            (no name)
    ...

    [devices.json テンプレート] が末尾に表示されるのでコピーして使ってください。
"""

import asyncio
import json
import os
import sys

# scripts/ から src/ を import できるように PYTHONPATH を調整
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from dotenv import load_dotenv
from src.main import generate_sign

# プロジェクトルートの .env も読む
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


async def fetch_device_list(token: str, secret: str) -> tuple[dict, dict]:
    sign, t, nonce = generate_sign(token, secret)
    headers = {
        "Authorization": token,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json; charset=utf8",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.switch-bot.com/v1.1/devices",
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        rate_info = {
            "limit": resp.headers.get("x-ratelimit-limit", "N/A"),
            "remaining": resp.headers.get("x-ratelimit-remaining", "N/A"),
            "reset": resp.headers.get("x-ratelimit-reset", "N/A"),
        }
        return resp.json(), rate_info


def print_devices(data: dict) -> None:
    body = data.get("body", {})
    physical = body.get("deviceList", [])
    virtual = body.get("infraredRemoteList", [])

    # --- Physical devices ---
    print("\n[Physical Devices]")
    if not physical:
        print("  (なし)")
    else:
        header = f"{'No.':<4}  {'deviceId':<22}  {'deviceType':<28}  {'deviceName'}"
        print(header)
        print("-" * len(header))
        for i, d in enumerate(physical, 1):
            print(
                f"{i:<4}  {d.get('deviceId', ''):<22}  "
                f"{d.get('deviceType', ''):<28}  {d.get('deviceName', '')}"
            )

    # --- IR / Virtual devices ---
    if virtual:
        print("\n[Infrared Remote / Virtual Devices]")
        header = f"{'No.':<4}  {'remoteId':<22}  {'remoteType':<28}  {'remoteName'}"
        print(header)
        print("-" * len(header))
        for i, d in enumerate(virtual, 1):
            print(
                f"{i:<4}  {d.get('deviceId', ''):<22}  "
                f"{d.get('remoteType', ''):<28}  {d.get('deviceName', '')}"
            )

    # --- devices.json テンプレート ---
    plug_minis = [
        d
        for d in physical
        if "plug" in d.get("deviceType", "").lower()
        or "Plug" in d.get("deviceType", "")
    ]

    if plug_minis:
        print("\n[devices.json テンプレート (Plug Mini のみ抽出)]")
        template = [
            {
                "id": d["deviceId"],
                "name": d.get("deviceName", "plug_mini").replace(" ", "_").lower(),
                "room": "work",
                "shelf": "rack_1",
                "parent_id": "none",
            }
            for d in plug_minis
        ]
        print(json.dumps(template, ensure_ascii=False, indent=2))
    else:
        print("\n[devices.json テンプレート (全 Physical デバイス)]")
        template = [
            {
                "id": d["deviceId"],
                "name": d.get("deviceName", "device").replace(" ", "_").lower(),
                "room": "work",
                "shelf": "rack_1",
                "parent_id": "none",
            }
            for d in physical
        ]
        print(json.dumps(template, ensure_ascii=False, indent=2))


async def main() -> None:
    token = os.getenv("SWITCHBOT_TOKEN")
    secret = os.getenv("SWITCHBOT_SECRET")

    if not token or not secret:
        print(
            "ERROR: SWITCHBOT_TOKEN または SWITCHBOT_SECRET が未設定です。\n"
            "  export SWITCHBOT_TOKEN='...'  SWITCHBOT_SECRET='...' をセットしてください。\n"
            "  または services/exporter/.env に記載してください。"
        )
        sys.exit(1)

    print("SwitchBot API へ接続中...", end="", flush=True)
    data, rate_info = await fetch_device_list(token, secret)
    print(" OK")

    status_code = data.get("statusCode")
    if status_code != 100:
        print(f"API Error (statusCode={status_code}): {data.get('message')}")
        sys.exit(1)

    print("\n[API Rate Limit]")
    print(f"  Limit:     {rate_info['limit']} calls/day")
    print(f"  Remaining: {rate_info['remaining']}")
    print(f"  Reset:     {rate_info['reset']} (epoch ms)")

    print_devices(data)


if __name__ == "__main__":
    asyncio.run(main())
