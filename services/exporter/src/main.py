import os
import time
import asyncio
import random
from prometheus_client import start_http_server, Gauge


# メトリクス定義
POWER_WATT = Gauge(
    "switchbot_power_watts", "Current power in Watts", ["room", "shelf", "device_id"]
)
API_REMAINING = Gauge("switchbot_api_requests_remaining", "Daily API limit remaining")


async def run_exporter():
    is_mock = os.getenv("MOCK_MODE", "false").lower() == "true"
    port = int(os.getenv("EXPORTER_PORT", 8000))

    start_http_server(port)
    print(f"Exporter started on port {port} (Mock: {is_mock})")

    while True:
        if is_mock:
            # モックデータ生成ロジック
            mock_val = random.uniform(5.0, 150.0)
            POWER_WATT.labels(room="work", shelf="rack_1", device_id="MOCK-001").set(
                mock_val
            )
            API_REMAINING.set(9999)
            print(f"[MOCK] Scraped value: {mock_val:.2f}W")
        else:
            # TODO: ここに実際の API 取得ロジックを実装
            pass

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_exporter())
