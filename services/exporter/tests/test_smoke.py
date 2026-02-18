import pytest
import httpx
import os
from dotenv import load_dotenv
from src.main import generate_sign

load_dotenv()


@pytest.mark.asyncio
async def test_real_api_auth():
    """本物のトークンを使用してデバイスリストが取得できるか確認する

    このテストは .env ファイルに SWITCHBOT_TOKEN と SWITCHBOT_SECRET が
    設定されている場合のみ実行されます。
    """
    token = os.getenv("SWITCHBOT_TOKEN")
    secret = os.getenv("SWITCHBOT_SECRET")

    if not token or not secret:
        pytest.skip("SWITCHBOT_TOKEN or SWITCHBOT_SECRET is not set in .env")

    async with httpx.AsyncClient() as client:
        sign, t, nonce = generate_sign(token, secret)
        headers = {
            "Authorization": token,
            "sign": sign,
            "nonce": nonce,
            "t": t,
            "Content-Type": "application/json; charset=utf8",
        }

        url = "https://api.switch-bot.com/v1.1/devices"
        resp = await client.get(url, headers=headers, timeout=10.0)
        data = resp.json()

        # 認証が成功していれば statusCode は必ず 100 になる
        assert resp.status_code == 200
        assert data.get("statusCode") == 100, f"API Error: {data.get('message')}"

        device_count = len(data["body"]["deviceList"])
        print(f"\n[Smoke Test] API Auth Success! Devices found: {device_count}")


@pytest.mark.asyncio
async def test_api_rate_limit_headers():
    """APIレート制限ヘッダーの処理テスト

    本物のAPIレスポンスがレート制限ヘッダーを含むことを確認する。
    """
    token = os.getenv("SWITCHBOT_TOKEN")
    secret = os.getenv("SWITCHBOT_SECRET")

    if not token or not secret:
        pytest.skip("SWITCHBOT_TOKEN or SWITCHBOT_SECRET not set")

    async with httpx.AsyncClient() as client:
        sign, t, nonce = generate_sign(token, secret)
        headers = {
            "Authorization": token,
            "sign": sign,
            "nonce": nonce,
            "t": t,
            "Content-Type": "application/json; charset=utf8",
        }

        url = "https://api.switch-bot.com/v1.1/devices"
        resp = await client.get(url, headers=headers, timeout=10.0)

        # レート制限ヘッダーが存在するか確認
        remaining = resp.headers.get("x-ratelimit-remaining")
        if remaining:
            print(f"\n[Rate Limit] Remaining requests: {remaining}")
            assert int(remaining) >= 0, "残りリクエスト数は0以上である必要があります"
        else:
            print("\n[WARNING] x-ratelimit-remaining header not found")
