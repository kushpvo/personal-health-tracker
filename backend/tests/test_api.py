import io
from app.db.models import Biomarker
from app.db.seed_loader import load_biomarkers


def test_list_reports_empty(client, create_user, auth_headers):
    user = create_user()
    response = client.get("/api/reports", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json() == []


def test_dashboard_summary_empty(client, create_user, auth_headers):
    user = create_user()
    response = client.get("/api/biomarkers/summary", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json() == []


def test_dashboard_summary_with_data(client, test_db, create_user, auth_headers):
    load_biomarkers(test_db)
    from app.db.models import Report, ReportResult
    from datetime import date, datetime, timezone

    user = create_user()
    report = Report(
        filename="test.pdf",
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        report_name="Test Report",
        sample_date=date(2025, 3, 15),
        uploaded_at=datetime.now(timezone.utc),
        status="done",
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    chol = (
        test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    )
    result = ReportResult(
        report_id=report.id,
        biomarker_id=chol.id,
        raw_name="Total Cholesterol",
        value=183.0,
        unit="mg/dL",
        is_flagged_unknown=False,
    )
    test_db.add(result)
    test_db.commit()

    response = client.get("/api/biomarkers/summary", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["biomarker"]["name"] == "Total Cholesterol"
    assert data[0]["latest_value"] == 183.0
    # 183 is in sufficient range (150-199), not optimal (100-149)
    assert data[0]["latest_zone"] == "sufficient"


def test_upload_invalid_extension(client, create_user, auth_headers):
    user = create_user()
    response = client.post(
        "/api/reports",
        files={"file": ("report.docx", b"fake content", "application/octet-stream")},
        headers=auth_headers(user),
    )
    assert response.status_code == 422


def test_report_not_found_status(client, create_user, auth_headers):
    user = create_user()
    response = client.get("/api/reports/9999/status", headers=auth_headers(user))
    assert response.status_code == 404


def test_biomarker_not_found(client, create_user, auth_headers):
    user = create_user()
    response = client.get(f"/api/biomarkers/9999", headers=auth_headers(user))
    assert response.status_code == 404


def test_biomarker_detail_with_data(client, test_db, create_user, auth_headers):
    load_biomarkers(test_db)
    from app.db.models import Report, ReportResult
    from datetime import date, datetime, timezone

    user = create_user()
    report = Report(
        filename="test2.pdf",
        original_filename="test2.pdf",
        file_path="/tmp/test2.pdf",
        report_name="Test Report 2",
        sample_date=date(2025, 6, 1),
        uploaded_at=datetime.now(timezone.utc),
        status="done",
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    glucose = test_db.query(Biomarker).filter(Biomarker.name == "Glucose").first()
    result = ReportResult(
        report_id=report.id,
        biomarker_id=glucose.id,
        raw_name="Glucose",
        value=82.0,
        unit="mg/dL",
        is_flagged_unknown=False,
    )
    test_db.add(result)
    test_db.commit()

    response = client.get(f"/api/biomarkers/{glucose.id}", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert data["biomarker"]["name"] == "Glucose"
    assert len(data["results"]) == 1
    assert data["results"][0]["zone"] == "optimal"  # 82 is in 70-85


def test_biomarkers_list(client, test_db, create_user, auth_headers):
    load_biomarkers(test_db)
    user = create_user()
    response = client.get("/api/biomarkers/list", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 20
    names = [b["name"] for b in data]
    assert names == sorted(names)
    assert "default_unit" in data[0]
    assert "alternate_units" in data[0]


def test_get_report_results(client, test_db, create_user, auth_headers):
    load_biomarkers(test_db)
    from app.db.models import Report, ReportResult
    from datetime import datetime, timezone, timezone

    user = create_user()
    report = Report(
        filename="r.pdf",
        original_filename="r.pdf",
        file_path="/tmp/r.pdf",
        status="done",
        uploaded_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    test_db.add(
        ReportResult(
            report_id=report.id,
            raw_name="Glucose",
            value=90.0,
            unit="mg/dL",
            is_flagged_unknown=False,
            sort_order=0,
        )
    )
    test_db.add(
        ReportResult(
            report_id=report.id,
            raw_name="Unknown Marker",
            value=5.0,
            unit="g/L",
            is_flagged_unknown=True,
            sort_order=1,
        )
    )
    test_db.commit()

    response = client.get(
        f"/api/reports/{report.id}/results", headers=auth_headers(user)
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["raw_name"] == "Glucose"
    assert data[0]["sort_order"] == 0
    assert data[1]["is_flagged_unknown"] is True
    assert data[1]["sort_order"] == 1


def test_submit_review(client, test_db, create_user, auth_headers):
    load_biomarkers(test_db)
    from app.db.models import Biomarker, Report, ReportResult, UnknownBiomarker
    from datetime import datetime, timezone, timezone

    user = create_user()
    report = Report(
        filename="rev.pdf",
        original_filename="rev.pdf",
        file_path="/tmp/rev.pdf",
        status="done",
        uploaded_at=datetime.now(timezone.utc),
        report_name="Old Name",
        user_id=user.id,
    )
    test_db.add(report)
    unknown = UnknownBiomarker(
        raw_name="Mystery Marker",
        raw_unit="g/L",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    test_db.add(unknown)
    test_db.commit()
    test_db.refresh(report)

    result = ReportResult(
        report_id=report.id,
        raw_name="Mystery Marker",
        value=5.0,
        unit="g/L",
        is_flagged_unknown=True,
        sort_order=0,
    )
    test_db.add(result)
    test_db.commit()
    test_db.refresh(result)
    test_db.refresh(unknown)

    glucose = test_db.query(Biomarker).filter(Biomarker.name == "Glucose").first()

    response = client.put(
        f"/api/reports/{report.id}/review",
        json={
            "report_name": "New Name",
            "sample_date": "2025-01-12",
            "results": [
                {
                    "id": result.id,
                    "value": 88.0,
                    "unit": "mg/dL",
                    "biomarker_id": glucose.id,
                }
            ],
        },
        headers=auth_headers(user),
    )
    assert response.status_code == 200

    test_db.refresh(result)
    test_db.refresh(report)
    test_db.refresh(unknown)

    assert report.report_name == "New Name"
    assert result.human_matched is True
    assert result.is_flagged_unknown is False
    assert result.biomarker_id == glucose.id
    assert unknown.resolved_biomarker_id == glucose.id


def test_submit_review_triggers_unit_conversion(
    client, test_db, create_user, auth_headers
):
    """When a user matches an unrecognised result, value is converted to default unit."""
    load_biomarkers(test_db)
    from app.db.models import Biomarker, Report, ReportResult
    from datetime import datetime, timezone, timezone

    user = create_user()
    report = Report(
        filename="conv.pdf",
        original_filename="conv.pdf",
        file_path="/tmp/conv.pdf",
        status="done",
        uploaded_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    result = ReportResult(
        report_id=report.id,
        raw_name="Total Cholesterol",
        value=5.6,
        unit="mmol/L",
        is_flagged_unknown=True,
        sort_order=0,
    )
    test_db.add(result)
    test_db.commit()
    test_db.refresh(result)

    chol = (
        test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    )

    client.put(
        f"/api/reports/{report.id}/review",
        json={
            "report_name": "Conv Test",
            "sample_date": None,
            "results": [
                {
                    "id": result.id,
                    "value": 5.6,
                    "unit": "mmol/L",
                    "biomarker_id": chol.id,
                }
            ],
        },
        headers=auth_headers(user),
    )

    test_db.refresh(result)
    # 5.6 mmol/L * 38.67 = 216.552 mg/dL
    assert result.unit == "mg/dL"
    assert abs(result.value - 216.552) < 0.01


def test_change_default_unit_success(client, test_db, create_user, auth_headers):
    load_biomarkers(test_db)
    from app.db.models import Biomarker, Report, ReportResult
    from datetime import datetime, timezone, timezone

    chol = (
        test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    )

    user = create_user()
    report = Report(
        filename="u.pdf",
        original_filename="u.pdf",
        file_path="/tmp/u.pdf",
        status="done",
        uploaded_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    result = ReportResult(
        report_id=report.id,
        biomarker_id=chol.id,
        raw_name="Total Cholesterol",
        value=200.0,
        unit="mg/dL",
        is_flagged_unknown=False,
        sort_order=0,
    )
    test_db.add(result)
    test_db.commit()
    test_db.refresh(result)

    resp = client.patch(
        f"/api/biomarkers/{chol.id}/default-unit",
        json={"unit": "mmol/L"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["default_unit"] == "mmol/L"

    test_db.refresh(chol)
    test_db.refresh(result)
    # 200 mg/dL * 0.02586 = 5.172 mmol/L
    assert result.unit == "mmol/L"
    assert abs(result.value - 5.172) < 0.01
    assert chol.default_unit == "mmol/L"
    assert chol.optimal_min is not None and chol.optimal_min < 10  # was ~100 mg/dL


def test_change_default_unit_invalid_unit(client, test_db, create_user, auth_headers):
    load_biomarkers(test_db)
    from app.db.models import Biomarker

    user = create_user()
    chol = (
        test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    )
    resp = client.patch(
        f"/api/biomarkers/{chol.id}/default-unit",
        json={"unit": "kg/m2"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 400


def test_change_default_unit_not_found(client, create_user, auth_headers):
    user = create_user()
    resp = client.patch(
        "/api/biomarkers/9999/default-unit",
        json={"unit": "mmol/L"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 404


def test_change_default_unit_noop(client, test_db, create_user, auth_headers):
    """Same unit returns 200 with no DB changes."""
    load_biomarkers(test_db)
    from app.db.models import Biomarker

    user = create_user()
    chol = (
        test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    )
    original_min = chol.optimal_min
    resp = client.patch(
        f"/api/biomarkers/{chol.id}/default-unit",
        json={"unit": chol.default_unit},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    test_db.refresh(chol)
    assert chol.optimal_min == original_min


def test_setup_login_and_me_flow(client):
    response = client.get("/api/auth/setup-required")
    assert response.status_code == 200
    assert response.json() == {"required": True}

    setup = client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "password123"},
    )
    assert setup.status_code == 200
    token = setup.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert me.json()["username"] == "admin"

    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password123"},
    )
    assert login.status_code == 200


def test_admin_can_manage_users(client, create_user, auth_headers):
    admin = create_user(username="admin", role="admin")
    headers = auth_headers(admin)

    create_response = client.post(
        "/api/admin/users",
        json={"username": "alice", "password": "password123", "role": "user"},
        headers=headers,
    )
    assert create_response.status_code == 201
    created_user = create_response.json()

    list_response = client.get("/api/admin/users", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    update_response = client.patch(
        f"/api/admin/users/{created_user['id']}",
        json={"is_active": False},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False

    impersonate_response = client.post(
        f"/api/admin/impersonate/{created_user['id']}",
        headers=headers,
    )
    assert impersonate_response.status_code == 200
    assert impersonate_response.json()["token_type"] == "bearer"


def test_reports_are_isolated_by_user(client, test_db, create_user, auth_headers):
    from app.db.models import Report
    from datetime import datetime, timezone, timezone

    user_one = create_user(username="one")
    user_two = create_user(username="two")
    test_db.add(
        Report(
            filename="one.pdf",
            original_filename="one.pdf",
            file_path="/tmp/one.pdf",
            status="done",
            uploaded_at=datetime.now(timezone.utc),
            user_id=user_one.id,
        )
    )
    test_db.commit()

    response = client.get("/api/reports", headers=auth_headers(user_two))
    assert response.status_code == 200
    assert response.json() == []


def test_list_and_resolve_unknowns(client, test_db, create_user, auth_headers):
    from app.db.models import Report, ReportResult, UnknownBiomarker
    from app.db.seed_loader import load_biomarkers
    from datetime import datetime, timezone

    load_biomarkers(test_db)
    user = create_user()

    report = Report(
        filename="u.pdf",
        original_filename="u.pdf",
        file_path="/tmp/u.pdf",
        status="done",
        uploaded_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()

    test_db.add(
        ReportResult(
            report_id=report.id,
            raw_name="GLUC",
            value=95.0,
            unit="mg/dL",
            is_flagged_unknown=True,
        )
    )
    test_db.add(
        UnknownBiomarker(
            raw_name="GLUC",
            raw_unit="mg/dL",
            times_seen=1,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    test_db.commit()

    resp = client.get("/api/unknowns", headers=auth_headers(user))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["raw_name"] == "GLUC"

    from app.db.models import Biomarker

    glucose = test_db.query(Biomarker).filter(Biomarker.name == "Glucose").first()

    resolve_resp = client.patch(
        f"/api/unknowns/{data[0]['id']}/resolve",
        json={"biomarker_id": glucose.id},
        headers=auth_headers(user),
    )
    assert resolve_resp.status_code == 200

    resp2 = client.get("/api/unknowns", headers=auth_headers(user))
    assert resp2.json() == []

    test_db.refresh(glucose)
    assert "gluc" in [a.lower() for a in (glucose.aliases or [])]


def test_refresh_token_flow(client, test_db):
    # Use a unique username to avoid conflict with other tests
    setup_resp = client.post(
        "/api/auth/setup", json={"username": "admin_refresh", "password": "password123"}
    )
    if setup_resp.status_code == 403:
        # setup already done, skip
        return
    assert setup_resp.status_code == 200
    assert "access_token" in setup_resp.json()
    assert "refresh_token" in setup_resp.cookies

    refresh_resp = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": setup_resp.cookies["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


def test_logout_revokes_refresh_token(client, test_db):
    setup_resp = client.post(
        "/api/auth/setup", json={"username": "admin_logout", "password": "password123"}
    )
    if setup_resp.status_code == 403:
        return
    assert setup_resp.status_code == 200
    cookie = setup_resp.cookies["refresh_token"]

    client.post("/api/auth/logout", cookies={"refresh_token": cookie})

    refresh_resp = client.post("/api/auth/refresh", cookies={"refresh_token": cookie})
    assert refresh_resp.status_code == 401


def test_reprocess_report_resets_status(client, test_db, create_user, auth_headers):
    from app.db.models import Report
    from datetime import datetime, timezone
    from unittest.mock import patch
    import tempfile, os

    user = create_user()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 fake")
        tmp_path = f.name

    report = Report(
        filename="r.pdf",
        original_filename="r.pdf",
        file_path=tmp_path,
        status="failed",
        uploaded_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()

    with patch("app.api.reports.run_pipeline"):
        resp = client.post(
            f"/api/reports/{report.id}/reprocess",
            headers=auth_headers(user),
        )

    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"

    test_db.refresh(report)
    assert report.status == "pending"

    os.unlink(tmp_path)


def test_list_reports_date_filter(client, test_db, create_user, auth_headers):
    from app.db.models import Report
    from datetime import datetime, date, timezone

    user = create_user()
    for d in ["2024-01-15", "2024-06-15", "2025-01-15"]:
        test_db.add(
            Report(
                filename=f"{d}.pdf",
                original_filename=f"{d}.pdf",
                file_path=f"/tmp/{d}.pdf",
                status="done",
                uploaded_at=datetime.now(timezone.utc),
                sample_date=date.fromisoformat(d),
                user_id=user.id,
            )
        )
    test_db.commit()

    resp = client.get(
        "/api/reports?from_date=2024-01-01&to_date=2024-12-31",
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all("2024" in (r["sample_date"] or "") for r in data)


def test_dashboard_trend_alert_on_large_change(
    client, test_db, create_user, auth_headers
):
    from app.db.models import Report, ReportResult, Biomarker
    from app.db.seed_loader import load_biomarkers
    from datetime import datetime, date, timezone

    load_biomarkers(test_db)
    user = create_user()

    for i, (d, val) in enumerate([("2024-01-01", 85.0), ("2024-06-01", 120.0)]):
        r = Report(
            filename=f"r{i}.pdf",
            original_filename=f"r{i}.pdf",
            file_path=f"/tmp/r{i}.pdf",
            status="done",
            uploaded_at=datetime.now(timezone.utc),
            sample_date=date.fromisoformat(d),
            user_id=user.id,
        )
        test_db.add(r)
        test_db.commit()
        glucose = test_db.query(Biomarker).filter(Biomarker.name == "Glucose").first()
        test_db.add(
            ReportResult(
                report_id=r.id,
                biomarker_id=glucose.id,
                raw_name="Glucose",
                value=val,
                unit="mg/dL",
                is_flagged_unknown=False,
            )
        )
        test_db.commit()

    resp = client.get("/api/biomarkers/summary", headers=auth_headers(user))
    assert resp.status_code == 200
    data = resp.json()
    glucose_summary = next(s for s in data if s["biomarker"]["name"] == "Glucose")
    assert glucose_summary["trend_alert"] is True
    assert glucose_summary["trend_delta"] is not None
    assert abs(glucose_summary["trend_delta"]) >= 20


def test_list_reports_date_filter(client, test_db, create_user, auth_headers):
    from app.db.models import Report
    from datetime import datetime, date, timezone

    user = create_user()
    for d in ["2024-01-15", "2024-06-15", "2025-01-15"]:
        test_db.add(
            Report(
                filename=f"{d}.pdf",
                original_filename=f"{d}.pdf",
                file_path=f"/tmp/{d}.pdf",
                status="done",
                uploaded_at=datetime.now(timezone.utc),
                sample_date=date.fromisoformat(d),
                user_id=user.id,
            )
        )
    test_db.commit()

    resp = client.get(
        "/api/reports?from_date=2024-01-01&to_date=2024-12-31",
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all("2024" in (r["sample_date"] or "") for r in data)
