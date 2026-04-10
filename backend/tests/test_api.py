import io
from app.db.models import Biomarker
from app.db.seed_loader import load_biomarkers


def test_list_reports_empty(client):
    response = client.get("/api/reports")
    assert response.status_code == 200
    assert response.json() == []


def test_dashboard_summary_empty(client):
    response = client.get("/api/biomarkers/summary")
    assert response.status_code == 200
    assert response.json() == []


def test_dashboard_summary_with_data(client, test_db):
    load_biomarkers(test_db)
    from app.db.models import Report, ReportResult
    from datetime import date, datetime

    report = Report(
        filename="test.pdf",
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        report_name="Test Report",
        sample_date=date(2025, 3, 15),
        uploaded_at=datetime.utcnow(),
        status="done",
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    chol = test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
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

    response = client.get("/api/biomarkers/summary")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["biomarker"]["name"] == "Total Cholesterol"
    assert data[0]["latest_value"] == 183.0
    # 183 is in sufficient range (150-199), not optimal (100-149)
    assert data[0]["latest_zone"] == "sufficient"


def test_upload_invalid_extension(client):
    response = client.post(
        "/api/reports",
        files={"file": ("report.docx", b"fake content", "application/octet-stream")},
    )
    assert response.status_code == 422


def test_report_not_found_status(client):
    response = client.get("/api/reports/9999/status")
    assert response.status_code == 404


def test_biomarker_not_found(client):
    response = client.get("/api/biomarkers/9999")
    assert response.status_code == 404


def test_biomarker_detail_with_data(client, test_db):
    load_biomarkers(test_db)
    from app.db.models import Report, ReportResult
    from datetime import date, datetime

    report = Report(
        filename="test2.pdf",
        original_filename="test2.pdf",
        file_path="/tmp/test2.pdf",
        report_name="Test Report 2",
        sample_date=date(2025, 6, 1),
        uploaded_at=datetime.utcnow(),
        status="done",
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

    response = client.get(f"/api/biomarkers/{glucose.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["biomarker"]["name"] == "Glucose"
    assert len(data["results"]) == 1
    assert data["results"][0]["zone"] == "optimal"  # 82 is in 70-85


def test_biomarkers_list(client, test_db):
    load_biomarkers(test_db)
    response = client.get("/api/biomarkers/list")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 20
    names = [b["name"] for b in data]
    assert names == sorted(names)
    assert "default_unit" in data[0]
    assert "alternate_units" in data[0]


def test_get_report_results(client, test_db):
    load_biomarkers(test_db)
    from app.db.models import Report, ReportResult
    from datetime import datetime

    report = Report(
        filename="r.pdf", original_filename="r.pdf", file_path="/tmp/r.pdf",
        status="done", uploaded_at=datetime.utcnow(),
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    test_db.add(ReportResult(
        report_id=report.id, raw_name="Glucose", value=90.0,
        unit="mg/dL", is_flagged_unknown=False, sort_order=0,
    ))
    test_db.add(ReportResult(
        report_id=report.id, raw_name="Unknown Marker", value=5.0,
        unit="g/L", is_flagged_unknown=True, sort_order=1,
    ))
    test_db.commit()

    response = client.get(f"/api/reports/{report.id}/results")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["raw_name"] == "Glucose"
    assert data[0]["sort_order"] == 0
    assert data[1]["is_flagged_unknown"] is True
    assert data[1]["sort_order"] == 1


def test_submit_review(client, test_db):
    load_biomarkers(test_db)
    from app.db.models import Biomarker, Report, ReportResult, UnknownBiomarker
    from datetime import datetime

    report = Report(
        filename="rev.pdf", original_filename="rev.pdf", file_path="/tmp/rev.pdf",
        status="done", uploaded_at=datetime.utcnow(), report_name="Old Name",
    )
    test_db.add(report)
    unknown = UnknownBiomarker(
        raw_name="Mystery Marker", raw_unit="g/L",
        first_seen_at=datetime.utcnow(), last_seen_at=datetime.utcnow(),
    )
    test_db.add(unknown)
    test_db.commit()
    test_db.refresh(report)

    result = ReportResult(
        report_id=report.id, raw_name="Mystery Marker",
        value=5.0, unit="g/L", is_flagged_unknown=True, sort_order=0,
    )
    test_db.add(result)
    test_db.commit()
    test_db.refresh(result)
    test_db.refresh(unknown)

    glucose = test_db.query(Biomarker).filter(Biomarker.name == "Glucose").first()

    response = client.put(f"/api/reports/{report.id}/review", json={
        "report_name": "New Name",
        "sample_date": "2025-01-12",
        "results": [{"id": result.id, "value": 88.0, "unit": "mg/dL", "biomarker_id": glucose.id}],
    })
    assert response.status_code == 200

    test_db.refresh(result)
    test_db.refresh(report)
    test_db.refresh(unknown)

    assert report.report_name == "New Name"
    assert result.human_matched is True
    assert result.is_flagged_unknown is False
    assert result.biomarker_id == glucose.id
    assert unknown.resolved_biomarker_id == glucose.id


def test_submit_review_triggers_unit_conversion(client, test_db):
    """When a user matches an unrecognised result, value is converted to default unit."""
    load_biomarkers(test_db)
    from app.db.models import Biomarker, Report, ReportResult
    from datetime import datetime

    report = Report(
        filename="conv.pdf", original_filename="conv.pdf", file_path="/tmp/conv.pdf",
        status="done", uploaded_at=datetime.utcnow(),
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    result = ReportResult(
        report_id=report.id, raw_name="Total Cholesterol",
        value=5.6, unit="mmol/L", is_flagged_unknown=True, sort_order=0,
    )
    test_db.add(result)
    test_db.commit()
    test_db.refresh(result)

    chol = test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()

    client.put(f"/api/reports/{report.id}/review", json={
        "report_name": "Conv Test",
        "sample_date": None,
        "results": [{"id": result.id, "value": 5.6, "unit": "mmol/L", "biomarker_id": chol.id}],
    })

    test_db.refresh(result)
    # 5.6 mmol/L * 38.67 = 216.552 mg/dL
    assert result.unit == "mg/dL"
    assert abs(result.value - 216.552) < 0.01


def test_change_default_unit_success(client, test_db):
    load_biomarkers(test_db)
    from app.db.models import Biomarker, Report, ReportResult
    from datetime import datetime

    chol = test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()

    report = Report(
        filename="u.pdf", original_filename="u.pdf", file_path="/tmp/u.pdf",
        status="done", uploaded_at=datetime.utcnow(),
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    result = ReportResult(
        report_id=report.id, biomarker_id=chol.id,
        raw_name="Total Cholesterol", value=200.0, unit="mg/dL",
        is_flagged_unknown=False, sort_order=0,
    )
    test_db.add(result)
    test_db.commit()
    test_db.refresh(result)

    resp = client.patch(f"/api/biomarkers/{chol.id}/default-unit", json={"unit": "mmol/L"})
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


def test_change_default_unit_invalid_unit(client, test_db):
    load_biomarkers(test_db)
    from app.db.models import Biomarker
    chol = test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    resp = client.patch(f"/api/biomarkers/{chol.id}/default-unit", json={"unit": "kg/m2"})
    assert resp.status_code == 400


def test_change_default_unit_not_found(client):
    resp = client.patch("/api/biomarkers/9999/default-unit", json={"unit": "mmol/L"})
    assert resp.status_code == 404


def test_change_default_unit_noop(client, test_db):
    """Same unit returns 200 with no DB changes."""
    load_biomarkers(test_db)
    from app.db.models import Biomarker
    chol = test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    original_min = chol.optimal_min
    resp = client.patch(f"/api/biomarkers/{chol.id}/default-unit", json={"unit": chol.default_unit})
    assert resp.status_code == 200
    test_db.refresh(chol)
    assert chol.optimal_min == original_min
