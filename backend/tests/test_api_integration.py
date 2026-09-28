"""
API integration tests — exercise every endpoint through the real FastAPI
app (via TestClient), the same way the frontend does. These formalize
what was previously ad-hoc manual verification during development,
including regression tests for real bugs found along the way:

- Requesting the same column twice from /data/{id}/series used to 500
  (pandas returns a DataFrame instead of a Series for a duplicate column
  selection, and .tolist() on that fails).
- numpy.bool_ values leaking into pre_whitening/trend_free_pre_whitening
  results used to break JSON serialization (pydantic can't serialize
  numpy's bool type, only Python's).
- A chart that failed to render server-side used to vanish silently with
  no trace anywhere, including in the summary text claiming it was embedded.

Most tests below run as one authenticated user (registered once via the
`_authenticate` autouse fixture, which attaches the token to every request
made through the shared `client`). Auth-specific behavior — rejecting
unauthenticated requests, and enforcing that one user cannot see another
user's datasets — is covered separately near the end of this file.
"""
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

# The database persists between separate `pytest` invocations (that
# persistence is the whole point of it in the real app), but several tests
# below use fixed email addresses for readability — so without this, a
# second test run would fail on "email already registered" rather than
# actually testing anything. Wiping the relevant tables here makes every
# pytest run start from a clean slate, the same way a real CI run would.
#
# This must work identically against both SQLite (local dev/CI) and a real
# Postgres database (this app's production target) — an earlier version of
# this reset deleted a local SQLite file directly, which silently did
# nothing at all once the app was pointed at Postgres via
# STATSCHOLAR_DATABASE_URL, and the exact "email already registered"
# failure this comment describes came back the moment a second test run
# happened against Postgres. Deleting rows through the app's own engine
# instead works the same way regardless of which database is configured.
from app.core.db import (
    datasets_table,
    email_verification_tokens_table,
    engine,
    password_reset_tokens_table,
    users_table,
)

with engine.begin() as _conn:
    _conn.execute(delete(datasets_table))
    _conn.execute(delete(email_verification_tokens_table))
    _conn.execute(delete(password_reset_tokens_table))
    _conn.execute(delete(users_table))

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def _authenticate():
    """Registers one throwaway user for this test module, verifies them
    (real functionality now requires a verified account — see
    require_verified_user in routers/auth.py), and attaches their token
    to every request the shared `client` makes from here on. This lets
    the bulk of the test file stay exactly as it was rather than
    threading auth headers through every single call site."""
    import logging
    import random
    import re

    email = f"testuser{random.randint(100000, 999999)}@example.com"
    resp = client.post("/auth/register", json={"email": email, "password": "testpassword123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    logger = logging.getLogger("app.services.email_service")
    handler = logging.StreamHandler()
    log_stream = handler.stream = __import__("io").StringIO()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    client.post("/auth/resend-verification")
    verify_token = re.search(r"token=([\w-]+)", log_stream.getvalue()).group(1)
    logger.removeHandler(handler)

    verify_resp = client.post("/auth/verify-email", json={"token": verify_token})
    assert verify_resp.status_code == 200, verify_resp.text
    yield


@pytest.fixture
def uploaded_dataset():
    """A 20-year x 4-quarter synthetic dataset, uploaded fresh for each test."""
    import random
    random.seed(0)
    lines = ["year,quarter,discharge_m3s,rainfall_mm,temp_c"]
    for y in range(2005, 2025):
        for q in range(4):
            t = (y - 2005) * 4 + q
            discharge = 420 + t * 2.8 + q * 6 + random.uniform(-12, 12)
            rainfall = 210 - t * 0.3 + random.uniform(-15, 15)
            temp = 14.5 + t * 0.03 + random.uniform(-0.2, 0.2)
            lines.append(f"{y},{q},{discharge:.1f},{rainfall:.1f},{temp:.2f}")
    csv = "\n".join(lines)
    files = {"file": ("test.csv", io.BytesIO(csv.encode()), "text/csv")}
    resp = client.post("/data/upload", files=files)
    assert resp.status_code == 200
    return resp.json()


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_rejects_unsupported_file_type():
    files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
    resp = client.post("/data/upload", files=files)
    assert resp.status_code == 400


def test_upload_returns_column_types_and_quality_score(uploaded_dataset):
    assert uploaded_dataset["row_count"] == 80
    assert len(uploaded_dataset["columns"]) == 5
    assert 0 <= uploaded_dataset["quality_score"] <= 100


def test_get_dataset_summary_by_id(uploaded_dataset):
    resp = client.get(f"/data/{uploaded_dataset['dataset_id']}")
    assert resp.status_code == 200
    assert resp.json()["row_count"] == 80


def test_get_dataset_summary_unknown_id_404():
    resp = client.get("/data/does-not-exist")
    assert resp.status_code == 404


def test_series_endpoint_returns_aligned_arrays(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    resp = client.get(f"/data/{did}/series", params={"columns": "year,discharge_m3s"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["year"]) == len(data["discharge_m3s"]) == 80


def test_series_endpoint_duplicate_column_does_not_500(uploaded_dataset):
    """Regression test: this exact request used to crash with a 500."""
    did = uploaded_dataset["dataset_id"]
    resp = client.get(f"/data/{did}/series", params={"columns": "quarter,quarter"})
    assert resp.status_code == 200
    assert resp.json()["quarter"] is not None


def test_series_endpoint_unknown_column_400(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    resp = client.get(f"/data/{did}/series", params={"columns": "year,nonexistent"})
    assert resp.status_code == 400


def test_descriptive_statistics(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    resp = client.get(f"/descriptive/{did}/discharge_m3s")
    assert resp.status_code == 200
    body = resp.json()
    assert "mean" in body and "sd" in body and "shapiro_wilk_p" in body


@pytest.mark.parametrize("test_id", [
    "mann_kendall", "sens_slope", "modified_mann_kendall", "pre_whitening", "tfpw",
])
def test_all_non_seasonal_trend_tests_run_successfully(uploaded_dataset, test_id):
    """Regression test: pre_whitening and tfpw used to 500 on numpy.bool_
    serialization — this would catch that class of bug again."""
    did = uploaded_dataset["dataset_id"]
    resp = client.post("/trend/run", json={
        "dataset_id": did, "variable": "discharge_m3s", "time_column": "year",
        "test": test_id, "mode": "student",
    })
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert "student_text" in body["interpretation"]
    assert "research_text" in body["interpretation"]


def test_seasonal_mann_kendall_requires_season_column(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    resp = client.post("/trend/run", json={
        "dataset_id": did, "variable": "discharge_m3s", "time_column": "year",
        "test": "seasonal_mann_kendall", "mode": "student",
    })
    assert resp.status_code == 400


def test_seasonal_mann_kendall_runs_with_season_column(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    resp = client.post("/trend/run", json={
        "dataset_id": did, "variable": "discharge_m3s", "time_column": "year",
        "test": "seasonal_mann_kendall", "season_column": "quarter", "mode": "research",
    })
    assert resp.status_code == 200
    assert "homogeneity_p" in resp.json()["statistics"]


def test_trend_unknown_test_400(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    resp = client.post("/trend/run", json={
        "dataset_id": did, "variable": "discharge_m3s", "time_column": "year",
        "test": "not_a_real_test", "mode": "student",
    })
    assert resp.status_code == 400


@pytest.mark.parametrize("method", ["pearson", "spearman", "kendall"])
def test_correlation_all_methods(uploaded_dataset, method):
    did = uploaded_dataset["dataset_id"]
    resp = client.post("/correlation/run", json={
        "dataset_id": did, "variables": ["discharge_m3s", "rainfall_mm"],
        "method": method, "mode": "student",
    })
    assert resp.status_code == 200
    assert len(resp.json()["matrix"]) == 2


def test_regression_runs_and_flags_assumptions(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    resp = client.post("/regression/run", json={
        "dataset_id": did, "predictor": "rainfall_mm", "outcome": "discharge_m3s", "mode": "student",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "r_squared" in body
    assert isinstance(body["interpretation"]["flags"], list)


def test_visualization_recommendations(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    resp = client.get(f"/visualization/{did}/recommend")
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert len(recs) > 0
    # The known quality fix: a low-cardinality grouping column like
    # "quarter" should never be recommended as a line-chart target.
    line_targets = [r["columns"][1] for r in recs if r["chart_type"] == "line"]
    assert "quarter" not in line_targets


def test_visualization_ignores_system_index_as_time_column():
    """Regression test: a Google Earth Engine-style export with both
    'system:index' (an incidentally-sequential row ID) and 'Year' used to
    pick 'system:index' as the time axis and even suggest the nonsensical
    'Year over system:index'. 'Year' must win, and 'system:index' must not
    appear anywhere in the recommendations."""
    csv_lines = ["system:index,Year,Mean_NDVI,Mean_TCI,Mean_VCI"]
    for i in range(20):
        year = 2005 + i
        csv_lines.append(f"{i}_0,{year},{0.4 + i * 0.01:.3f},{50 + i * 0.5:.2f},{45 + i * 0.6:.2f}")
    csv = "\n".join(csv_lines)
    files = {"file": ("t.csv", io.BytesIO(csv.encode()), "text/csv")}
    resp = client.post("/data/upload", files=files)
    did = resp.json()["dataset_id"]

    resp = client.get(f"/visualization/{did}/recommend")
    recs = resp.json()["recommendations"]

    all_columns_mentioned = [c for r in recs for c in r["columns"]]
    assert "system:index" not in all_columns_mentioned

    line_recs = [r for r in recs if r["chart_type"] == "line"]
    assert len(line_recs) > 0
    for r in line_recs:
        assert r["columns"][0] == "Year"


def test_report_export_docx(uploaded_dataset):
    resp = client.post("/report/export/docx", json={
        "project_title": "Test", "sections": [{"title": "A", "text": "Some text."}],
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/vnd.openxmlformats")


def test_docx_export_embeds_real_chart_image(uploaded_dataset):
    """Regression coverage for the chart-embedding feature: confirms the
    exported DOCX contains an actual image file, not just text, when a
    section includes a chart spec."""
    import zipfile
    did = uploaded_dataset["dataset_id"]
    sections = [{
        "title": "Trend Analysis", "text": "Discharge increases over time.",
        "chart": {"dataset_id": did, "chart_type": "line", "columns": ["year", "discharge_m3s"], "title": "test chart"},
    }]
    resp = client.post("/report/export/docx", json={"project_title": "T", "sections": sections})
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        media_files = [n for n in z.namelist() if n.startswith("word/media/")]
        assert len(media_files) == 1
        assert media_files[0].endswith(".png")


def test_pdf_export_embeds_real_chart_image(uploaded_dataset):
    """Same coverage for PDF: a section with a chart spec should produce a
    meaningfully larger file than the same section without one."""
    did = uploaded_dataset["dataset_id"]
    text_only = [{"title": "A", "text": "Some text with no chart."}]
    with_chart = [{
        "title": "A", "text": "Some text with no chart.",
        "chart": {"dataset_id": did, "chart_type": "scatter", "columns": ["discharge_m3s", "rainfall_mm"], "title": "t"},
    }]
    r1 = client.post("/report/export/pdf", json={"project_title": "T", "sections": text_only})
    r2 = client.post("/report/export/pdf", json={"project_title": "T", "sections": with_chart})
    assert r1.status_code == 200 and r2.status_code == 200
    assert len(r2.content) > len(r1.content) + 5000  # a real embedded image adds many KB, not a few bytes


def test_report_export_all_four_chart_types(uploaded_dataset):
    did = uploaded_dataset["dataset_id"]
    specs = [
        {"chart_type": "line", "columns": ["year", "discharge_m3s"]},
        {"chart_type": "scatter", "columns": ["discharge_m3s", "rainfall_mm"]},
        {"chart_type": "bar", "columns": ["quarter", "discharge_m3s"]},
        {"chart_type": "heatmap", "columns": ["discharge_m3s", "rainfall_mm", "temp_c"]},
    ]
    sections = [{"title": f"Chart {i}", "text": "x", "chart": {**spec, "dataset_id": did, "title": ""}} for i, spec in enumerate(specs)]
    resp = client.post("/report/export/pdf", json={"project_title": "T", "sections": sections})
    assert resp.status_code == 200


def test_docx_export_includes_real_table(uploaded_dataset):
    """Confirms a section with a `tables` spec produces an actual Word
    table (a <w:tbl> element), not just plain text listing the values."""
    import zipfile
    sections = [{
        "title": "Figures & tables", "text": "1 table included below.",
        "tables": [{"title": "Descriptive Statistics", "headers": ["Variable", "Mean"], "rows": [["year", "2014.5"]]}],
    }]
    resp = client.post("/report/export/docx", json={"project_title": "T", "sections": sections})
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        document_xml = z.read("word/document.xml").decode("utf-8")
        assert "<w:tbl>" in document_xml
        assert "Descriptive Statistics" in document_xml
        assert "2014.5" in document_xml


def test_pdf_export_includes_real_table(uploaded_dataset):
    """A section with a table should produce a meaningfully larger PDF
    than the same section without one — a real Table flowable, not just
    the values folded into the paragraph text."""
    text_only = [{"title": "A", "text": "No table here."}]
    with_table = [{
        "title": "A", "text": "No table here.",
        "tables": [{"title": "Stats", "headers": ["Variable", "Mean", "SD"], "rows": [["x", "1.0", "2.0"], ["y", "3.0", "4.0"]]}],
    }]
    r1 = client.post("/report/export/pdf", json={"project_title": "T", "sections": text_only})
    r2 = client.post("/report/export/pdf", json={"project_title": "T", "sections": with_table})
    assert r1.status_code == 200 and r2.status_code == 200
    assert len(r2.content) > len(r1.content)


def test_report_export_multiple_tables_in_one_section(uploaded_dataset):
    sections = [{
        "title": "Figures & tables", "text": "2 tables.",
        "tables": [
            {"title": "Descriptive Statistics", "headers": ["Variable", "Mean"], "rows": [["year", "2014.5"]]},
            {"title": "Correlation Matrix", "headers": ["", "a", "b"], "rows": [["a", "1.00", "0.5"], ["b", "0.5", "1.00"]]},
        ],
    }]
    r_docx = client.post("/report/export/docx", json={"project_title": "T", "sections": sections})
    r_pdf = client.post("/report/export/pdf", json={"project_title": "T", "sections": sections})
    assert r_docx.status_code == 200
    assert r_pdf.status_code == 200


def test_bad_chart_spec_does_not_break_export():
    """A chart referencing a nonexistent dataset should be skipped
    silently, not crash the whole report the user is trying to download."""
    sections = [{
        "title": "A", "text": "Text should still appear.",
        "chart": {"dataset_id": "does-not-exist", "chart_type": "line", "columns": ["x", "y"], "title": ""},
    }]
    resp = client.post("/report/export/pdf", json={"project_title": "T", "sections": sections})
    assert resp.status_code == 200


def test_bad_chart_spec_failure_is_logged(caplog):
    """Regression test: a chart that fails to render used to be silently
    dropped with zero trace anywhere, which is exactly what caused a real
    report to claim '6 charts embedded' while only 5 images were actually
    present. The export should still succeed, but the failure must now
    show up in the logs."""
    import logging
    sections = [{
        "title": "A", "text": "x",
        "chart": {"dataset_id": "does-not-exist-xyz", "chart_type": "line", "columns": ["x", "y"], "title": "my chart"},
    }]
    with caplog.at_level(logging.ERROR):
        resp = client.post("/report/export/pdf", json={"project_title": "T", "sections": sections})
    assert resp.status_code == 200
    assert any("Chart rendering failed" in r.message for r in caplog.records)
    assert any("does-not-exist-xyz" in r.message for r in caplog.records)


def test_report_export_pdf_sanitizes_special_characters():
    """Regression test: Greek letters / subscripts used to render as solid
    black boxes in the PDF instead of raising an error or converting."""
    resp = client.post("/report/export/pdf", json={
        "project_title": "Test",
        "sections": [{"title": "A", "text": "tau shown as \u03c4, r\u2081, R\u00b2, \u03c7\u00b2"}],
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"

    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(resp.content))
    text = reader.pages[0].extract_text()
    assert "tau" in text
    assert "r1" in text
    assert "R^2" in text
    assert "chi^2" in text
    # None of the problem characters should survive into the PDF text layer
    for bad_char in ("\u03c4", "\u2081", "\u00b2", "\u03c7"):
        assert bad_char not in text


def test_dataset_persists_across_simulated_restart(uploaded_dataset):
    """Regression test: datasets used to live only in an in-memory dict,
    so an uploaded dataset would vanish on any backend restart (including
    uvicorn --reload triggering on a code change). Now backed by disk."""
    from app.services import data_service
    did = uploaded_dataset["dataset_id"]

    # Simulate a real process restart by clearing the in-memory caches —
    # the on-disk copy must still answer subsequent requests.
    data_service._DATASETS.clear()
    data_service._META.clear()

    resp = client.get(f"/data/{did}")
    assert resp.status_code == 200
    assert resp.json()["row_count"] == 80

    resp = client.get(f"/data/{did}/series", params={"columns": "year,discharge_m3s"})
    assert resp.status_code == 200
    assert len(resp.json()["year"]) == 80


def test_full_session_end_to_end(uploaded_dataset):
    """Simulates a real user session: run several analyses, then export
    a report built from their accumulated interpretations."""
    did = uploaded_dataset["dataset_id"]
    sections = []

    for test_id in ["mann_kendall", "sens_slope"]:
        r = client.post("/trend/run", json={
            "dataset_id": did, "variable": "discharge_m3s", "time_column": "year",
            "test": test_id, "mode": "student",
        })
        assert r.status_code == 200
        sections.append({"title": f"Trend — {test_id}", "text": r.json()["interpretation"]["student_text"]})

    r = client.post("/correlation/run", json={
        "dataset_id": did, "variables": ["discharge_m3s", "rainfall_mm"], "method": "pearson", "mode": "student",
    })
    assert r.status_code == 200
    sections.append({"title": "Correlation", "text": r.json()["interpretation"]["student_text"]})

    r = client.post("/regression/run", json={
        "dataset_id": did, "predictor": "rainfall_mm", "outcome": "discharge_m3s", "mode": "student",
    })
    assert r.status_code == 200
    sections.append({"title": "Regression", "text": r.json()["interpretation"]["student_text"]})

    docx_resp = client.post("/report/export/docx", json={"project_title": "E2E", "sections": sections})
    pdf_resp = client.post("/report/export/pdf", json={"project_title": "E2E", "sections": sections})
    assert docx_resp.status_code == 200
    assert pdf_resp.status_code == 200
    assert len(sections) == 4


# --------------------------------------------------------------------------
# Auth: registration, login, and — the part that actually matters — that
# one user genuinely cannot see another user's data. A login screen with
# no real isolation behind it is security theater, not a real feature.
# --------------------------------------------------------------------------

def _register(email, password="testpassword123"):
    return TestClient(app).post("/auth/register", json={"email": email, "password": password})


def _register_and_verify(email, password="testpassword123"):
    """For tests that need an account that can actually use the app
    (upload data, run analyses) — plain _register() leaves the account
    unverified, which require_verified_user now correctly blocks from
    every real endpoint."""
    import logging
    import re

    resp = _register(email, password)
    client_local = TestClient(app)
    client_local.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"

    logger = logging.getLogger("app.services.email_service")
    handler = logging.StreamHandler()
    log_stream = handler.stream = __import__("io").StringIO()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    client_local.post("/auth/resend-verification")
    verify_token = re.search(r"token=([\w-]+)", log_stream.getvalue()).group(1)
    logger.removeHandler(handler)

    assert client_local.post("/auth/verify-email", json={"token": verify_token}).status_code == 200
    return client_local


def test_register_new_user_succeeds():
    resp = _register("newuser1@example.com")
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == "newuser1@example.com"


def test_register_duplicate_email_rejected():
    _register("dupe@example.com")
    resp = _register("dupe@example.com")
    assert resp.status_code == 409


def test_register_short_password_rejected():
    resp = _register("shortpass@example.com", password="short")
    assert resp.status_code == 400


def test_login_correct_credentials_succeeds():
    _register("logintest@example.com", password="correctpassword")
    resp = TestClient(app).post("/auth/login", json={"email": "logintest@example.com", "password": "correctpassword"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_rejected():
    _register("wrongpass@example.com", password="correctpassword")
    resp = TestClient(app).post("/auth/login", json={"email": "wrongpass@example.com", "password": "nope"})
    assert resp.status_code == 401


def test_login_unknown_email_rejected():
    resp = TestClient(app).post("/auth/login", json={"email": "doesnotexist@example.com", "password": "whatever123"})
    assert resp.status_code == 401


def test_unauthenticated_request_rejected():
    """A request with no token at all must be rejected — using a fresh
    client with no Authorization header, not the shared authenticated one."""
    fresh_client = TestClient(app)
    resp = fresh_client.get("/data/some-id")
    assert resp.status_code == 401


def test_invalid_token_rejected():
    fresh_client = TestClient(app)
    fresh_client.headers["Authorization"] = "Bearer not-a-real-token"
    resp = fresh_client.get("/data/some-id")
    assert resp.status_code == 401


def test_users_list_requires_auth():
    fresh_client = TestClient(app)
    resp = fresh_client.get("/auth/users")
    assert resp.status_code == 401


def test_users_list_never_leaks_password_hash():
    resp = _register("listtest@example.com", password="verysecretpassword")
    token = resp.json()["access_token"]
    authed_client = TestClient(app)
    authed_client.headers["Authorization"] = f"Bearer {token}"

    resp = authed_client.get("/auth/users")
    assert resp.status_code == 200
    body = resp.json()
    assert "users" in body
    assert any(u["email"] == "listtest@example.com" for u in body["users"])
    # The real point of this test: no password data anywhere in the response
    assert "password_hash" not in resp.text
    assert "verysecretpassword" not in resp.text
    for u in body["users"]:
        assert set(u.keys()) == {"id", "email", "created_at", "is_verified"}


def test_me_endpoint_returns_current_user():
    resp = _register("metest@example.com")
    token = resp.json()["access_token"]
    authed_client = TestClient(app)
    authed_client.headers["Authorization"] = f"Bearer {token}"
    me_resp = authed_client.get("/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "metest@example.com"


def test_dataset_isolation_between_users():
    """The critical test: user A uploads a dataset, user B (a completely
    different account) must NOT be able to see it — not the summary, not
    the series data, not run any analysis against it. This is what makes
    per-user accounts a real security boundary rather than just a login
    screen sitting in front of one shared pool of data. Both accounts are
    verified here specifically so the 403s asserted below are genuinely
    the ownership check firing, not the separate verification check."""
    client_a = _register_and_verify("usera_isolation@example.com")
    client_b = _register_and_verify("userb_isolation@example.com")

    csv = "year,value\n" + "\n".join(f"{2000+i},{i*2}" for i in range(10))
    files = {"file": ("secret.csv", io.BytesIO(csv.encode()), "text/csv")}
    upload_resp = client_a.post("/data/upload", files=files)
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]

    # User A can access their own dataset
    assert client_a.get(f"/data/{dataset_id}").status_code == 200

    # User B must be forbidden — not just from the summary, but from every
    # endpoint that touches the dataset.
    assert client_b.get(f"/data/{dataset_id}").status_code == 403
    assert client_b.get(f"/data/{dataset_id}/series", params={"columns": "year,value"}).status_code == 403
    assert client_b.get(f"/descriptive/{dataset_id}/value").status_code == 403
    assert client_b.post("/trend/run", json={
        "dataset_id": dataset_id, "variable": "value", "time_column": "year",
        "test": "mann_kendall", "mode": "student",
    }).status_code == 403
    assert client_b.post("/correlation/run", json={
        "dataset_id": dataset_id, "variables": ["year", "value"], "method": "pearson", "mode": "student",
    }).status_code == 403
    assert client_b.post("/regression/run", json={
        "dataset_id": dataset_id, "predictor": "year", "outcome": "value", "mode": "student",
    }).status_code == 403
    assert client_b.get(f"/visualization/{dataset_id}/recommend").status_code == 403


def test_dataset_isolation_survives_restart():
    """Ownership must be enforced from the on-disk copy too, not just the
    in-memory cache — otherwise a backend restart would silently drop the
    ownership check along with the in-memory dict."""
    from app.services import data_service

    client_a = _register_and_verify("usera_restart@example.com")
    client_b = _register_and_verify("userb_restart@example.com")

    csv = "year,value\n" + "\n".join(f"{2000+i},{i*2}" for i in range(10))
    files = {"file": ("secret2.csv", io.BytesIO(csv.encode()), "text/csv")}
    dataset_id = client_a.post("/data/upload", files=files).json()["dataset_id"]

    # Simulate a real process restart
    data_service._DATASETS.clear()
    data_service._META.clear()

    assert client_a.get(f"/data/{dataset_id}").status_code == 200  # owner still works, from disk
    assert client_b.get(f"/data/{dataset_id}").status_code == 403  # non-owner still blocked, from disk


# --------------------------------------------------------------------------
# Email verification and password reset. SMTP is never configured in tests
# (or in a fresh local setup without credentials), so `send_email` logs the
# email content instead of sending it — these tests extract the token from
# that log output via pytest's `caplog`, the same way a developer reading
# their own terminal would in dev mode.
# --------------------------------------------------------------------------

import re


def _extract_token_from_log(caplog, link_path="verify-email"):
    """Registration always sends a verification email, even in tests that
    go on to test the password-reset flow — so a generic 'token=' search
    can grab the wrong token if more than one email was logged during the
    test. Anchoring on the specific link path ('verify-email' vs
    'reset-password') and taking the LAST match keeps this correct
    regardless of what else got logged earlier in the same test."""
    matches = re.findall(rf"{link_path}\?token=([\w-]+)", caplog.text)
    assert matches, f"No '{link_path}?token=' link found in logged email content:\n{caplog.text}"
    return matches[-1]


def test_new_user_starts_unverified():
    resp = _register("unverified@example.com")
    assert resp.json()["user"]["is_verified"] is False


def test_registration_sends_verification_email(caplog):
    import logging
    with caplog.at_level(logging.INFO):
        _register("getsemail@example.com")
    assert "Verify your StatScholar account" in caplog.text
    assert "verify-email?token=" in caplog.text


def test_verify_email_with_valid_token(caplog):
    import logging
    with caplog.at_level(logging.INFO):
        resp = _register("willverify@example.com")
    token_client = TestClient(app)
    token_client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    verify_token = _extract_token_from_log(caplog)

    resp = token_client.post("/auth/verify-email", json={"token": verify_token})
    assert resp.status_code == 200
    assert resp.json()["user"]["is_verified"] is True

    me = token_client.get("/auth/me")
    assert me.json()["is_verified"] is True


def test_verify_email_token_cannot_be_reused(caplog):
    import logging
    with caplog.at_level(logging.INFO):
        _register("reuseverify@example.com")
    verify_token = _extract_token_from_log(caplog)

    fresh = TestClient(app)
    assert fresh.post("/auth/verify-email", json={"token": verify_token}).status_code == 200
    assert fresh.post("/auth/verify-email", json={"token": verify_token}).status_code == 400


def test_verify_email_invalid_token_rejected():
    fresh = TestClient(app)
    resp = fresh.post("/auth/verify-email", json={"token": "not-a-real-token"})
    assert resp.status_code == 400


def test_resend_verification_requires_auth():
    fresh = TestClient(app)
    assert fresh.post("/auth/resend-verification").status_code == 401


def test_resend_verification_noop_when_already_verified(caplog):
    import logging
    with caplog.at_level(logging.INFO):
        resp = _register("alreadyverified@example.com")
    authed = TestClient(app)
    authed.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    verify_token = _extract_token_from_log(caplog)
    authed.post("/auth/verify-email", json={"token": verify_token})

    resp = authed.post("/auth/resend-verification")
    assert resp.status_code == 200
    assert "Already verified" in resp.json()["message"]


def test_forgot_password_same_response_for_unknown_email():
    """The critical security property: a request for a nonexistent email
    must look identical to one for a real email, or the endpoint becomes a
    way to probe which addresses have accounts here."""
    _register("realaccount@example.com")
    fresh = TestClient(app)
    resp_real = fresh.post("/auth/forgot-password", json={"email": "realaccount@example.com"})
    resp_fake = fresh.post("/auth/forgot-password", json={"email": "definitely-not-registered@example.com"})
    assert resp_real.status_code == resp_fake.status_code == 200
    assert resp_real.json() == resp_fake.json()


def test_forgot_password_sends_email_only_for_real_account(caplog):
    import logging
    _register("hasresetmail@example.com")
    fresh = TestClient(app)

    with caplog.at_level(logging.INFO):
        fresh.post("/auth/forgot-password", json={"email": "hasresetmail@example.com"})
    assert "reset-password?token=" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.INFO):
        fresh.post("/auth/forgot-password", json={"email": "nobodyhere@example.com"})
    assert "reset-password?token=" not in caplog.text


def test_reset_password_full_flow(caplog):
    import logging
    _register("fullreset@example.com", password="originalpassword123")
    fresh = TestClient(app)

    with caplog.at_level(logging.INFO):
        fresh.post("/auth/forgot-password", json={"email": "fullreset@example.com"})
    reset_token = _extract_token_from_log(caplog, "reset-password")

    resp = fresh.post("/auth/reset-password", json={"token": reset_token, "new_password": "brandnewpassword456"})
    assert resp.status_code == 200

    assert fresh.post("/auth/login", json={
        "email": "fullreset@example.com", "password": "originalpassword123",
    }).status_code == 401
    assert fresh.post("/auth/login", json={
        "email": "fullreset@example.com", "password": "brandnewpassword456",
    }).status_code == 200


def test_reset_password_token_cannot_be_reused(caplog):
    import logging
    _register("noreuse@example.com")
    fresh = TestClient(app)
    with caplog.at_level(logging.INFO):
        fresh.post("/auth/forgot-password", json={"email": "noreuse@example.com"})
    reset_token = _extract_token_from_log(caplog, "reset-password")

    assert fresh.post("/auth/reset-password", json={"token": reset_token, "new_password": "firstnewpass123"}).status_code == 200
    assert fresh.post("/auth/reset-password", json={"token": reset_token, "new_password": "secondnewpass456"}).status_code == 400


def test_reset_password_invalid_token_rejected():
    fresh = TestClient(app)
    resp = fresh.post("/auth/reset-password", json={"token": "garbage", "new_password": "somepassword123"})
    assert resp.status_code == 400


def test_reset_password_short_password_rejected(caplog):
    import logging
    _register("shortresetpw@example.com")
    fresh = TestClient(app)
    with caplog.at_level(logging.INFO):
        fresh.post("/auth/forgot-password", json={"email": "shortresetpw@example.com"})
    reset_token = _extract_token_from_log(caplog, "reset-password")

    resp = fresh.post("/auth/reset-password", json={"token": reset_token, "new_password": "short"})
    assert resp.status_code == 400


def test_password_reset_invalidates_previously_issued_tokens(caplog):
    """Regression test for a real gap found through end-to-end browser
    testing: JWTs are stateless, so simply changing the password hash used
    to leave any already-issued token (e.g. from a browser session that
    was compromised, which is often exactly why someone resets a password)
    still fully valid until it expired on its own — up to 7 days later.
    A reset must invalidate every token issued before it."""
    import logging
    resp = _register("invalidate@example.com", password="originalpassword123")
    old_token = resp.json()["access_token"]
    old_client = TestClient(app)
    old_client.headers["Authorization"] = f"Bearer {old_token}"
    assert old_client.get("/auth/me").status_code == 200  # works before the reset

    fresh = TestClient(app)
    with caplog.at_level(logging.INFO):
        fresh.post("/auth/forgot-password", json={"email": "invalidate@example.com"})
    reset_token = _extract_token_from_log(caplog, "reset-password")
    assert fresh.post("/auth/reset-password", json={
        "token": reset_token, "new_password": "brandnewpassword456",
    }).status_code == 200

    # The old token must now be rejected, even though it hasn't expired
    assert old_client.get("/auth/me").status_code == 401

    # A fresh login with the new password must still work fine
    new_login = fresh.post("/auth/login", json={
        "email": "invalidate@example.com", "password": "brandnewpassword456",
    })
    assert new_login.status_code == 200
    new_client = TestClient(app)
    new_client.headers["Authorization"] = f"Bearer {new_login.json()['access_token']}"
    assert new_client.get("/auth/me").status_code == 200


# --------------------------------------------------------------------------
# Email verification is required for actual app usage (uploading data,
# running analyses, exporting reports) — not just a checkbox that gets
# ticked eventually with no consequence. /auth/me and
# /auth/resend-verification remain accessible while unverified, since an
# unverified account still needs a way to check its own status and get a
# new verification link.
# --------------------------------------------------------------------------

def test_unverified_user_blocked_from_upload():
    unverified = _register("blockedupload@example.com").json()
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {unverified['access_token']}"
    csv = "year,value\n2020,1\n2021,2"
    resp = c.post("/data/upload", files={"file": ("t.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert resp.status_code == 403
    assert "verify" in resp.json()["detail"].lower()


def test_unverified_user_blocked_from_every_dataset_endpoint():
    """Upload as a verified account (needed to get a dataset_id at all),
    then confirm a SEPARATE unverified account is blocked from every
    endpoint that does real work against it — the same coverage as the
    ownership-isolation test, but for the verification gate instead."""
    owner = _register_and_verify("verifiedowner@example.com")
    csv = "year,value\n" + "\n".join(f"{2000+i},{i*2}" for i in range(10))
    dataset_id = owner.post("/data/upload", files={"file": ("t.csv", io.BytesIO(csv.encode()), "text/csv")}).json()["dataset_id"]

    unverified = _register("blockedeverywhere@example.com").json()
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {unverified['access_token']}"

    assert c.get(f"/data/{dataset_id}").status_code == 403
    assert c.get(f"/data/{dataset_id}/series", params={"columns": "year,value"}).status_code == 403
    assert c.get(f"/descriptive/{dataset_id}/value").status_code == 403
    assert c.post("/trend/run", json={
        "dataset_id": dataset_id, "variable": "value", "time_column": "year", "test": "mann_kendall", "mode": "student",
    }).status_code == 403
    assert c.post("/correlation/run", json={
        "dataset_id": dataset_id, "variables": ["year", "value"], "method": "pearson", "mode": "student",
    }).status_code == 403
    assert c.post("/regression/run", json={
        "dataset_id": dataset_id, "predictor": "year", "outcome": "value", "mode": "student",
    }).status_code == 403
    assert c.get(f"/visualization/{dataset_id}/recommend").status_code == 403
    assert c.post("/report/export/pdf", json={"project_title": "t", "sections": [{"title": "a", "text": "b"}]}).status_code == 403
    assert c.post("/report/export/docx", json={"project_title": "t", "sections": [{"title": "a", "text": "b"}]}).status_code == 403


def test_unverified_user_can_still_check_status_and_resend(caplog):
    """The gate must not lock an unverified account out of the two things
    it actually needs to become verified: checking its own status, and
    getting a fresh verification link."""
    import logging
    resp = _register("stillcheckable@example.com").json()
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {resp['access_token']}"

    me = c.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["is_verified"] is False

    with caplog.at_level(logging.INFO):
        resend = c.post("/auth/resend-verification")
    assert resend.status_code == 200
    assert "verify-email?token=" in caplog.text


def test_verifying_unlocks_previously_blocked_endpoints(caplog):
    import logging
    resp = _register("unlocks@example.com").json()
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {resp['access_token']}"

    csv = "year,value\n2020,1\n2021,2"
    files = {"file": ("t.csv", io.BytesIO(csv.encode()), "text/csv")}
    assert c.post("/data/upload", files=files).status_code == 403

    with caplog.at_level(logging.INFO):
        c.post("/auth/resend-verification")
    verify_token = _extract_token_from_log(caplog)
    assert c.post("/auth/verify-email", json={"token": verify_token}).status_code == 200

    assert c.post("/data/upload", files={"file": ("t.csv", io.BytesIO(csv.encode()), "text/csv")}).status_code == 200
