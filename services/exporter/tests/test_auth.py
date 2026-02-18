# services/exporter/tests/test_auth.py
import pytest
from src.main import generate_sign


def test_generate_sign_logic():
    """
    署名生成ロジックの『形式』をテストする。
    値が毎回変わる nonce/timestamp を含むため、
    ここでは「出力が仕様（Base64かつ大文字）に沿っているか」を確認する。
    """
    token = "test_token"
    secret = "test_secret"

    sign, t, nonce = generate_sign(token, secret)

    # 1. 署名が空でなく、Base64（A-Z, 0-9, =, +）の形式であること
    assert len(sign) > 0
    assert sign.isupper()  # SwitchBot API v1.1は英字は大文字指定

    # 2. タイムスタンプがミリ秒（13桁）程度であること
    assert len(t) >= 13
    assert t.isdigit()

    # 3. nonceがUUID形式（36文字）であること
    assert len(nonce) == 36
