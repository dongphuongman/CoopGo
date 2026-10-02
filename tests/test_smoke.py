"""Smoke tests — chạy: ./.venv/bin/pytest tests/ -q
Không cần DB thật (chỉ build app + hàm thuần).
"""
from fastapi.testclient import TestClient

import pytest

from app.factory import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _paths():
    app = create_app()
    return sorted({r.path for r in app.routes if hasattr(r, "path")})


def test_routes_wired():
    paths = _paths()
    for must in [
        "/health",
        "/fleet/phuong-tien", "/fleet/lai-xe", "/fleet/lai-xe/import",
        "/tuyen", "/phan-cong", "/lenh",
        "/templates/", "/render/{template_id}",
        "/bulk/render-fleet", "/verify/{code}", "/lenh-qr/{code}",
        "/alerts/expiry", "/dashboard/summary",
        "/xa-vien", "/config/",
    ]:
        assert must in paths, f"thiếu route {must}"


def test_health_no_db(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_protected_routes_need_token(client):
    assert client.get("/fleet/lai-xe").status_code in (401, 403)
    # public verify: 404 mã lạ nhưng KHÔNG 401
    assert client.get("/verify/ABCXYZ").status_code == 404


def test_vi_labels_have_accents():
    from app.services.ai_service import _rule_based_labels
    labels = _rule_based_labels(["bien_so_xe", "cccd_ben_a", "hinh_thuc_tt", "nam_tra"])
    assert labels["bien_so_xe"] == "Biển số xe"
    assert labels["cccd_ben_a"] == "CCCD bên A"
    assert labels["hinh_thuc_tt"] == "Hình thức TT"
    assert labels["nam_tra"] == "Năm trả"


def test_gplx_rules():
    from app.services.gplx_service import validate_gplx_for_so_cho
    ok, _ = validate_gplx_for_so_cho("E", 45)
    assert ok
    ok, _ = validate_gplx_for_so_cho("B2", 45)
    assert not ok
