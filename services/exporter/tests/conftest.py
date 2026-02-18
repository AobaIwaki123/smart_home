import pytest
import httpx


@pytest.fixture(scope="function")
async def client():
    """非同期HTTPクライアントをテスト用に提供するフィクスチャ"""
    async with httpx.AsyncClient() as client:
        yield client
