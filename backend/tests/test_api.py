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
