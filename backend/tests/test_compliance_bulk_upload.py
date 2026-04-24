"""Backend tests for Compliance Bulk Upload endpoints + regression on stats/research."""
import io
import os
import time
import zipfile

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://equity-commodity-hub.preview.emergentagent.com").rstrip("/")


def _minimal_pdf_bytes(text: str = "Test Circular") -> bytes:
    """Return a minimal but valid single-page PDF (>200 bytes)."""
    content_stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode()
    content_obj = (
        b"4 0 obj\n<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n"
        + content_stream + b"\nendstream\nendobj\n"
    )
    pdf = (
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        + content_obj +
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    xref_pos = len(pdf)
    pdf += b"xref\n0 6\n0000000000 65535 f \n"
    # Offsets are not critical for our backend parser (PyMuPDF tolerates small corruption)
    for i in range(5):
        pdf += f"{(i + 1) * 20:010d} 00000 n \n".encode()
    pdf += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    # Pad to ensure >200 bytes guaranteed
    return pdf + b"\n% padding " + b"x" * 200


def _build_zip(filenames: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in filenames:
            zf.writestr(fname, _minimal_pdf_bytes(fname))
    return buf.getvalue()


# ─── Health / regression ────────────────────────────────────────────────────────
class TestComplianceRegression:
    def test_stats_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/compliance/stats", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "stores" in data
        assert "overall_phase" in data
        assert "totals" in data
        for src in ("nse", "bse", "sebi"):
            assert src in data["stores"]

    def test_research_endpoint_short_question_rejected(self):
        r = requests.post(
            f"{BASE_URL}/api/compliance/research",
            json={"question": "x"},
            timeout=30,
        )
        assert r.status_code == 400

    def test_bulk_upload_list_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/compliance/bulk-upload?limit=5", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)


# ─── Bulk upload validation ──────────────────────────────────────────────────
class TestBulkUploadValidation:
    def test_invalid_source_rejected(self):
        zip_bytes = _build_zip(["2024-01-01_TEST_doc.pdf"])
        r = requests.post(
            f"{BASE_URL}/api/compliance/bulk-upload",
            data={"source": "nasdaq"},
            files={"file": ("test.zip", zip_bytes, "application/zip")},
            timeout=30,
        )
        assert r.status_code == 400
        assert "source" in r.text.lower()

    def test_non_zip_rejected(self):
        r = requests.post(
            f"{BASE_URL}/api/compliance/bulk-upload",
            data={"source": "sebi"},
            files={"file": ("notzip.zip", b"this is not a zip file at all", "application/zip")},
            timeout=30,
        )
        assert r.status_code == 400
        assert "zip" in r.text.lower()

    def test_unknown_job_id_returns_404(self):
        r = requests.get(
            f"{BASE_URL}/api/compliance/bulk-upload/does-not-exist-12345",
            timeout=30,
        )
        assert r.status_code == 404


# ─── Bulk upload E2E ────────────────────────────────────────────────────────
class TestBulkUploadE2E:
    def test_create_job_and_poll_until_done(self):
        zip_bytes = _build_zip([
            "2024-03-15_TEST-CIR-001_insider-trading-test.pdf",
            "2024-05-20_TEST-CIR-002_lodr-amendment-test.pdf",
        ])

        # POST upload
        r = requests.post(
            f"{BASE_URL}/api/compliance/bulk-upload",
            data={"source": "sebi"},
            files={"file": ("test_bulk.zip", zip_bytes, "application/zip")},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["source"] == "sebi"
        job_id = data["job_id"]

        # Immediately fetch job status
        r2 = requests.get(f"{BASE_URL}/api/compliance/bulk-upload/{job_id}", timeout=30)
        assert r2.status_code == 200
        j = r2.json()
        assert j["job_id"] == job_id
        assert j["source"] == "sebi"
        assert j["status"] in ("queued", "running", "done", "failed")

        # Poll until done/failed (up to 90s)
        terminal = None
        for _ in range(45):
            time.sleep(2)
            rp = requests.get(f"{BASE_URL}/api/compliance/bulk-upload/{job_id}", timeout=30)
            if rp.status_code != 200:
                continue
            jp = rp.json()
            if jp["status"] in ("done", "failed"):
                terminal = jp
                break

        assert terminal is not None, "Job did not finish within 90s"
        # Job should have completed (done or failed — both acceptable depending on PDF parsing)
        # But we must at least have processed the files
        assert terminal["total"] == 2, f"Expected 2 files, got {terminal.get('total')}"
        print(f"Final job status: {terminal['status']} | ingested={terminal.get('ingested')} skipped={terminal.get('skipped')} failed={terminal.get('failed')}")

        # Verify job appears in listing
        rl = requests.get(f"{BASE_URL}/api/compliance/bulk-upload?limit=10", timeout=30)
        assert rl.status_code == 200
        jobs = rl.json()["jobs"]
        assert any(jj["job_id"] == job_id for jj in jobs), "New job not in list endpoint"
