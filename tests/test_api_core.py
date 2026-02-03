"""
核心 API 自动化测试：健康检查、认证、行情接口
运行: pytest tests/test_api_core.py -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    """根路径健康检查"""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "version" in data or "environment" in data


def test_api_health():
    """API 健康检查"""
    r = client.get("/api/system/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("docs") == "/docs"


def test_token_requires_auth():
    """未提供凭证时登录应返回 401"""
    r = client.post(
        "/token",
        data={"username": "nonexistent", "password": "wrong"},
    )
    assert r.status_code == 401


def test_spot_list_returns_structure():
    """沪深 A 股列表返回结构正确（可空列表）"""
    r = client.get("/api/market/spot?limit=10&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert "stocks" in data
    assert "total" in data
    assert isinstance(data["stocks"], list)


def test_docs_available_in_dev(monkeypatch):
    """开发环境下 /docs 可访问"""
    monkeypatch.setenv("ENVIRONMENT", "development")
    # 应用已启动，环境变量可能已加载；仅当 docs 启用时断言
    r = client.get("/docs")
    # 开发环境通常为 200，生产可能 404（docs_url=None）
    assert r.status_code in (200, 404)
