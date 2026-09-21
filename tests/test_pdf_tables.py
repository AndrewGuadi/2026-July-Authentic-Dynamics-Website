import base64
import copy
import io
import json
import random
import re
from contextlib import closing

import pypdfium2 as pdfium
import pytest
from PIL import Image, ImageChops, ImageStat

from authentic_dynamics import create_app
from authentic_dynamics.blueprints.tools import pdf_tables
from authentic_dynamics.blueprints.tools.converters import ConversionError, convert_json
from authentic_dynamics.blueprints.tools.pdf_tables import (
    BOTTOM_MARGIN,
    MARGIN,
    TABLE_TOP,
    build_pdf,
    render_pdf_page,
    validate_plan,
)

REFERENCE = [
    {"ID": "001", "Customer": "Maya", "Notes": "Delivery near the café."},
    {"ID": "002", "Customer": "Alex", "Notes": "Second row."},
]


def inspect_pdf(data, summary, check_boxes=True):
    """Use PDFium (not the PDF writer) to inspect selectable text and ink positions."""
    texts = []
    with pdfium.PdfDocument(data) as document:
        assert len(document) == summary["page_count"]
        for page in document:
            width, height = page.get_size()
            assert (width > height) == (summary["orientation"] == "landscape")
            with closing(page.get_textpage()) as text:
                texts.append(text.get_text_range())
                if check_boxes:
                    for index in range(text.count_chars()):
                        if not text.get_text_range(index, 1).strip():
                            continue
                        left, bottom, right, top = text.get_charbox(index)
                        assert MARGIN - 1 <= left <= right <= width - MARGIN + 1
                        # Includes title and footer as well as table content.
                        assert 15 <= bottom <= top <= height - 20
            page.close()
    return texts


@pytest.mark.parametrize("orientation", ["portrait", "landscape", "auto"])
@pytest.mark.parametrize("size", [10, 11, 12])
def test_readable_export_selectable_text_and_bounds(orientation, size):
    data, summary, plan = build_pdf(REFERENCE, orientation=orientation, font_size=size)
    text = "\n".join(inspect_pdf(data, summary))
    assert '001' in text and 'café' in text and 'Second row.' in text
    assert summary['font_size'] == size
    assert len(plan.pages) == 1


def test_long_cell_preserves_all_tokens_across_pages():
    tokens = [f"TOKEN{i:05d}" for i in range(10000)]
    body = ' '.join(tokens)  # Over 100,000 characters in one cell.
    data, summary, plan = build_pdf([{'id': '001', 'body': body}])
    assert summary['page_count'] > 1
    texts = inspect_pdf(data, summary, check_boxes=False)
    assert re.findall(r'TOKEN\d{5}', '\n'.join(texts)) == tokens
    assert all('body' in text and 'id' in text for text in texts)
    assert 'continued' in texts[-1]
    assert plan.continuations > 0
    assert summary['shortened_cells'] == 0


def test_url_whitespace_empty_nested_and_unicode():
    source = [{'url': 'https://example.test/' + 'abcdef123456' * 200,
               'text': 'First\n\n  indented  text\tend\r\nLast',
               'nested': {'a': [1, None, '001']}, 'missing': None},
              {'text': 'Café Ω Ж 中文 😀 مرحبا e\u0301'}]
    data, summary, plan = build_pdf(source)
    texts = inspect_pdf(data, summary)
    assert 'Café' in ''.join(texts) and 'Ж' in ''.join(texts)
    assert any('Unicode' in warning for warning in summary['warnings'])
    assert '\\u4e2d' in ''.join(texts)
    validate_plan(plan)
    assert plan.sections[0]['rows'][0][1].startswith('First\n\n  indented  text')
    assert plan.sections[0]['rows'][0][2] == '{"a": [1, null, "001"]}'


def test_column_order_selection_wide_table_and_minimum_font():
    source = [{f'field{i}': f'value{i}' for i in range(20)}]
    with pytest.raises(ConversionError, match='Choose columns'):
        build_pdf(source)
    _, summary, plan = build_pdf(source, columns=['field19', 'field1'])
    assert plan.sections[0]['headers'] == ['field19', 'field1']
    assert summary['column_count'] == 2
    _, summary, _ = build_pdf(source, columns=[f'field{i}' for i in range(10)])
    assert summary['orientation'] == 'landscape'
    with pytest.raises(ConversionError, match='landscape'):
        build_pdf(source, orientation='portrait', columns=[f'field{i}' for i in range(10)])


def test_appendix_preserves_content_and_shortening_is_explicit():
    value = 'UNIQUE START ' + 'long content ' * 400 + ' UNIQUE END'
    data, summary, plan = build_pdf([{'id': 1, 'notes': value}], long_cells='appendix')
    assert summary['appendix_values'] == 1 and summary['shortened_cells'] == 0
    assert value in plan.sections[1]['rows'][0][0]
    texts = inspect_pdf(data, summary)
    assert 'See appendix A1' in texts[0] and 'UNIQUE END' in texts[-1]
    data, summary, _ = build_pdf([{'notes': value}], long_cells='shorten')
    text = ''.join(inspect_pdf(data, summary))
    assert 'SHORTENED' in text and 'UNIQUE END' not in text
    assert summary['shortened_cells'] == 1
    assert any('incomplete' in message for message in summary['warnings'])


def test_rows_near_page_boundary_are_not_lost_or_duplicated():
    source = [{'ID': f'ID{i:04d}', 'value': 'Some wrapped words ' * (1 + i % 6)} for i in range(90)]
    data, summary, plan = build_pdf(source, orientation='portrait')
    texts = inspect_pdf(data, summary)
    assert re.findall(r'ID\d{4}', '\n'.join(texts)) == [row['ID'] for row in source]
    assert all('value' in text for text in texts)
    for page in plan.pages:
        assert min(cell.top for cell in page.cells) == TABLE_TOP
        assert max(cell.top + cell.height for cell in page.cells) <= plan.height - BOTTOM_MARGIN + 0.01


def test_deterministic_generated_cases_and_corruption_checks():
    rng = random.Random(8721)
    for _ in range(8):
        source = [{f'key{column}': ''.join(rng.choices('abc éΩ\n ', k=rng.randint(0, 300)))
                   for column in range(rng.randint(1, 6))} for _ in range(rng.randint(1, 12))]
        data, summary, plan = build_pdf(source)
        validate_plan(plan)
        inspect_pdf(data, summary)
    data, _, plan = build_pdf(REFERENCE)
    assert data == build_pdf(REFERENCE)[0]
    for mutation in ['overflow', 'overlap', 'missing', 'small', 'height']:
        bad = copy.deepcopy(plan)
        if mutation == 'overflow':
            bad.pages[0].cells[-1].x = bad.width
        elif mutation == 'overlap':
            bad.pages[0].cells[1].x = MARGIN
        elif mutation == 'missing':
            bad.pages[0].cells[-1].lines = []
        elif mutation == 'small':
            bad.font_size = 8
        else:
            bad.pages[0].cells[-1].height = 1
        with pytest.raises(ConversionError):
            validate_plan(bad)


@pytest.mark.parametrize('options', [
    {'font_size': 8}, {'orientation': 'wrong'}, {'long_cells': 'wrong'},
    {'columns': []}, {'columns': ['missing']}, {'columns': ['ID', 'ID']},
    {'columns': [1]}, {'columns': 'ID'},
])
def test_invalid_pdf_options(options):
    with pytest.raises(ConversionError):
        build_pdf(REFERENCE, **options)


def test_limits_and_preview_pages(monkeypatch):
    monkeypatch.setattr(pdf_tables, 'MAX_TEXT', 5)
    with pytest.raises(ConversionError, match='million'):
        build_pdf(REFERENCE)
    monkeypatch.setattr(pdf_tables, 'MAX_TEXT', 2_000_000)
    monkeypatch.setattr(pdf_tables, 'MAX_ROWS', 1)
    with pytest.raises(ConversionError, match='5,000'):
        build_pdf(REFERENCE)
    monkeypatch.setattr(pdf_tables, 'MAX_ROWS', 5000)
    monkeypatch.setattr(pdf_tables, 'MAX_PAGES', 1)
    with pytest.raises(ConversionError, match='200 pages'):
        build_pdf([{'long': 'long text ' * 3000}])
    data, _, _ = build_pdf(REFERENCE)
    with Image.open(io.BytesIO(render_pdf_page(data))) as image:
        assert image.width <= 1001 and image.height <= 1401
    for content, page in [(b'bad', 0), (b'%PDF-broken', 0), (data, -1), (data, 1)]:
        with pytest.raises(ConversionError):
            render_pdf_page(content, page)


def test_pdf_preview_download_routes_and_csrf():
    client = create_app({'TESTING': True, 'SECRET_KEY': 'test',
                         'SQLALCHEMY_DATABASE_URI': 'sqlite://'}).test_client()
    for endpoint in ['/tools/json-converter', '/tools/json-converter/pdf-page']:
        assert client.post(endpoint).status_code == 400
    page = client.get('/tools/json-converter').text
    token = re.search(r'name="csrf_token" value="([^"]+)"', page)[1]
    fields = {'csrf_token': token, 'json_text': json.dumps(REFERENCE), 'format': 'pdf',
              'pdf_columns': json.dumps(['Notes', 'ID']), 'pdf_orientation': 'landscape',
              'pdf_font_size': '12'}
    preview = client.post('/tools/json-converter', data={**fields, 'action': 'pdf_preview'},
                          headers={'Accept': 'application/json'})
    assert preview.status_code == 200 and preview.headers['Cache-Control'] == 'no-store'
    assert preview.json['summary']['column_count'] == 2
    data = base64.b64decode(preview.json['pdf'])
    direct = client.post('/tools/json-converter', data=fields)
    assert direct.data == data and direct.mimetype == 'application/pdf'
    inline = client.post('/tools/json-converter', data={**fields, 'action': 'pdf_preview'})
    assert inline.data == data and inline.headers['Content-Disposition'].startswith('inline')
    rendered = client.post('/tools/json-converter/pdf-page', data={
        'csrf_token': token, 'file': (io.BytesIO(data), 'preview.pdf'), 'page': '0'})
    assert rendered.status_code == 200
    assert rendered.data == base64.b64decode(preview.json['image'])
    assert rendered.headers['Cache-Control'] == 'no-store'
    for options in [{'pdf_font_size': '1'}, {'pdf_columns': '{'}, {'pdf_columns': '[]'}]:
        response = client.post('/tools/json-converter', data={**fields, **options},
                               headers={'Accept': 'application/json'})
        assert response.status_code == 400 and response.json['error']


def test_pdf_bypasses_excel_cell_limit():
    content = json.dumps({'long': 'complete ' * 5000}).encode()
    assert convert_json(content, 'pdf').startswith(b'%PDF-')
    with pytest.raises(ConversionError, match='32,768'):
        convert_json(content, 'xlsx')


def test_visual_reference():
    from pathlib import Path

    data, _, _ = build_pdf(REFERENCE)
    with Image.open(io.BytesIO(render_pdf_page(data))) as actual, Image.open(
        Path(__file__).parent / 'fixtures/pdf_table_reference.png'
    ) as expected:
        assert actual.size == expected.size
        difference = ImageChops.difference(actual.convert('RGB'), expected.convert('RGB'))
        # Small rasterizer differences are allowed; clipped/moved text or cells are not.
        assert max(ImageStat.Stat(difference).mean) < 1.0
