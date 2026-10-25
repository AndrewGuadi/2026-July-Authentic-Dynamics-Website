"""Preview must use the same interpretation and limits as the actual conversion."""

import io
import json

import pytest

from authentic_dynamics import create_app
from authentic_dynamics.blueprints.tools.converters import ConversionError, convert_csv


@pytest.fixture
def client():
    return create_app({"TESTING": True, "SECRET_KEY": "test", "WTF_CSRF_ENABLED": False,
                       "SQLALCHEMY_DATABASE_URI": "sqlite://"}).test_client()


@pytest.mark.parametrize("delimiter", [",", ";", "\t", "|"])
def test_csv_preview_uses_export_interpretation(delimiter):
    content = (f'code{delimiter}description\r\n001{delimiter}"two\nlines"\r\n'
               f'002{delimiter}"<script>alert(1)</script>"\r\n').encode()
    preview = convert_csv(content, "json", delimiter, True, preview=True)
    export = json.loads(convert_csv(content, "json", delimiter, True))
    assert preview["columns"] == ["code", "description"]
    assert [dict(zip(preview["columns"], row)) for row in preview["rows"]] == export
    assert preview["row_count"] == 2


def test_csv_preview_is_bounded_and_validates_whole_input():
    content = b"id,name\n" + b"001,Example\n" * 20
    preview = convert_csv(content, "xlsx", ",", True, preview=True)
    assert len(preview["rows"]) == 8
    assert preview["row_count"] == 20
    assert preview["truncated"] is True
    with pytest.raises(ConversionError, match="different number"):
        convert_csv(content + b"bad,row,extra\n", "xlsx", ",", True, preview=True)


def test_csv_preview_generated_headers_and_empty_records():
    preview = convert_csv(b"001,One\n", "tsv", ",", False, preview=True)
    assert preview["columns"] == ["column_1", "column_2"]
    assert preview["rows"] == [["001", "One"]]
    assert convert_csv(b"id,name\n", "json", ",", True, preview=True)["row_count"] == 0


def test_csv_preview_endpoint_returns_json_without_attachment(client):
    response = client.post("/tools/csv-converter", data={
        "file": (io.BytesIO(b"code,name\n001,Example\n"), "sample.csv"),
        "format": "xlsx", "headers": "on", "delimiter": ",", "action": "preview",
    }, headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.json["rows"] == [["001", "Example"]]
    assert "Content-Disposition" not in response.headers
    assert response.headers["Cache-Control"] == "no-store"


def test_csv_preview_response_size_is_bounded():
    cell = "x" * 32767
    preview = convert_csv(("name\n" + cell + "\n").encode(), "xlsx", ",", True,
                          preview=True)
    assert len(preview["rows"][0][0]) <= 301
    assert preview["cells_shortened"] is True


def test_tool_catalog_retains_all_links_without_javascript(client):
    page = client.get("/tools/").get_data(as_text=True)
    assert page.count('data-tool-job="') == 12
    assert 'data-tool-filters hidden' in page
    for slug in ["csv-converter", "pdf-to-image", "json-converter", "video-converter",
                 "list-cleaner", "free-invoice-maker", "local-ai", "qr-code-maker"]:
        assert f'href="/tools/{slug}"' in page
    assert 'href="/browser-xray"' in page

    assert 'href="/coding-calendar/"' in page
    assert 'href="/blog"' in page

    assert 'href="/tools/event-break-even"' in page
