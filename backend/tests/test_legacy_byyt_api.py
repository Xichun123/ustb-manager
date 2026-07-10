from app.main import app


def test_legacy_raw_byyt_routes_are_not_exposed():
    paths = app.openapi()["paths"]

    assert "/api/byyt/grades" not in paths
    assert "/api/byyt/profile" not in paths
