"""Opt-in real-browser regressions against an actual fixture-seeded FastAPI app.

Run WEB_UI_BROWSER_TESTS=1 python -m pytest tests/test_web_ui.py -q.
Requires node/chrome-devtools-axi and Chrome, but no network or model credentials.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import httpx
import pytest

from courseagent.dataflows.db import create_snapshot, init_db
from courseagent.dataflows.indexer import index_courses
from courseagent.dataflows.normalizer import normalize_courses
from courseagent.dataflows.parsers.uw_course_catalog import ParsedCourse
from courseagent.dataflows.source_registry import SourceRegistryEntry, register_source

pytestmark = pytest.mark.skipif(
    os.environ.get("WEB_UI_BROWSER_TESTS") != "1",
    reason="Set WEB_UI_BROWSER_TESTS=1 for chrome-devtools-axi browser regressions",
)


@pytest.fixture(scope="module")
def browser_app(tmp_path_factory):
    if not shutil.which("chrome-devtools-axi"):
        pytest.fail("chrome-devtools-axi is required for requested browser tests")
    root = Path(__file__).resolve().parents[1]
    data = tmp_path_factory.mktemp("web-ui")
    conn = init_db(data / "db.sqlite3")
    for department in ["CSE", "INFO"]:
        source = f"uw_{department.lower()}_catalog"
        url = f"https://www.washington.edu/students/crscat/{department.lower()}.html"
        register_source(conn, SourceRegistryEntry(
            id=source, name=f"UW {department} Catalog", tier=1, type="course_catalog",
            authority="official", department=department, url=url,
            allowed_url_patterns=(url,), extraction_policy="normalized_facts_allowed", promotion_rule=None,
        ))
        create_snapshot(conn, f"test-{department}", [source], status="indexed")
        courses = [ParsedCourse(department_code=department, course_number=number,
            title=title, description="Introductory programming and data methods.", credits="4")
            for number, title in ([('142', 'Computer Programming I'), ('143', 'Computer Programming II')]
                if department == 'CSE' else [('201', 'Technical Foundations')])]
        index_courses(conn, normalize_courses(courses, f"test-{department}", source),
            snapshot_id=f"test-{department}", source_id=source, source_title=f"UW {department} Catalog",
            url=url, source_document_id=f"test-doc-{department}", retrieved_at="2026-10-07T00:00:00Z")
    conn.close()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    runner = data / "serve.py"
    runner.write_text(
        "from pathlib import Path\nimport uvicorn\n"
        "from config.default_config import DefaultConfig\nfrom courseagent.api.app import create_app\n"
        f"data=Path({str(data)!r})\n"
        f"uvicorn.run(create_app(DefaultConfig(data_dir=data,db_path=data/'db.sqlite3')),host='127.0.0.1',port={port})\n"
    )
    log = (data / "server.log").open("w")
    process = subprocess.Popen([sys.executable, str(runner)], cwd=root,
        env={**os.environ, "PYTHONPATH": str(root)}, stdout=log, stderr=log)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if process.poll() is not None:
                pytest.fail((data / 'server.log').read_text())
            try:
                if httpx.get(url, timeout=0.2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            pytest.fail("UI test server did not become ready")
        yield url, {**os.environ, "CHROME_DEVTOOLS_AXI_SESSION": "research-agent-ui-regression"}
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()


def test_api_backed_search_detail_and_failure_states(browser_app):
    url, env = browser_app
    script = (Path(__file__).parent / "web_ui_browser.js").read_text().replace("__APP_URL__", url)
    result = subprocess.run(["chrome-devtools-axi", "run"], input=script,
        capture_output=True, text=True, env=env, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WEB_UI_PASS" in result.stdout, result.stdout + result.stderr


@pytest.mark.parametrize("width", [1440, 1100, 390, 320])
def test_search_and_open_detail_have_no_horizontal_overflow(browser_app, width):
    url, env = browser_app
    mobile = ",mobile,touch" if width < 500 else ""
    subprocess.run(["chrome-devtools-axi", "emulate", "--viewport", f"{width}x900x1{mobile}"],
        env=env, check=True, capture_output=True, text=True, timeout=30)
    script = f"""
await page.open('{url}');
await page.eval(() => {{document.querySelector('#query-input').value='CSE 142';}});
await page.click('.primary-button');
await page.wait(900);
console.log(JSON.stringify(await page.eval(() => {{
 const b=document.querySelector('.primary-button').getBoundingClientRect();
 const i=document.querySelector('#query-input').getBoundingClientRect();
 const ok=innerWidth==={width} && document.documentElement.scrollWidth===innerWidth &&
  !document.querySelector('.detail-panel').hidden && b.width>=44 && b.height>=44 && b.right<=innerWidth &&
  (innerWidth<=980 || Math.abs(b.top-i.top)<1);
 return {{ok,width:innerWidth,scroll:document.documentElement.scrollWidth,button:b.toJSON()}};
}})));
"""
    result = subprocess.run(["chrome-devtools-axi", "run"], input=script, env=env,
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"ok":true' in result.stdout, result.stdout + result.stderr
