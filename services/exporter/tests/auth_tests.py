import time
import hmac
import hashlib
import base64
import uuid
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


def test_auth():
    # 本来は K8s Secret 等から渡すが、テスト用に環境変数や直接入力を想定
    token = os.getenv("SWITCHBOT_TOKEN", "YOUR_TOKEN_HERE")
    secret = os.getenv("SWITCHBOT_SECRET", "YOUR_SECRET_HERE")

    nonce = str(uuid.uuid4())
    t = str(int(time.time() * 1000))
    string_to_sign = f"{token}{t}{nonce}"

    # 署名生成ロジック
    sign = base64.b64encode(
        hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    ).upper()

    headers = {
        "Authorization": token,
        "sign": str(sign, "utf-8"),
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json; charset=utf8",
    }

    url = "https://api.switch-bot.com/v1.1/devices"
    print(f"Testing Auth with URL: {url}...")

    response = requests.get(url, headers=headers)
    res_data = response.json()

    if res_data.get("statusCode") == 100:
        print("✅ Auth Success!")
        print(json.dumps(res_data, indent=2, ensure_ascii=False))
    else:
        print("❌ Auth Failed")
        print(f"Status Code: {res_data.get('statusCode')}")
        print(f"Message: {res_data.get('message')}")


if __name__ == "__main__":
    test_auth()
