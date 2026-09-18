import io
import json
import re
import zipfile
from xml.etree import ElementTree as ET

import pypdfium2 as pdfium
import pytest
from openpyxl import load_workbook
from PIL import Image

from authentic_dynamics import create_app
from authentic_dynamics.blueprints.tools.converters import ConversionError, convert_csv, convert_pdf


@pytest.fixture
def client():
    return create_app({"TESTING": True, "SECRET_KEY": "test", "WTF_CSRF_ENABLED": False,
                       "SQLALCHEMY_DATABASE_URI": "sqlite://"}).test_client()


def pdf_bytes(pages=1, width=72):
    with pdfium.PdfDocument.new() as document:
        for _ in range(pages):
            document.new_page(width, 72).close()
        output = io.BytesIO()
        document.save(output)
        return output.getvalue()


@pytest.mark.parametrize("path", ["/tools", "/tools/pdf-to-image", "/tools/csv-converter"])
def test_pages_and_no_nav_link(client, path):
    response = client.get(path)
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    nav = page.split('<nav id="nav"')[1].split('</nav>')[0]
    assert '/tools' not in nav
    assert 'aria-current="page"' not in nav
    assert client.get('/static/css/tools.css').status_code == 200
    assert client.get('/static/js/tools.js').status_code == 200


@pytest.mark.parametrize("format", ["png", "jpeg", "webp"])
def test_pdf_images(client, format):
    response = client.post('/tools/pdf-to-image', data={
        'file': (io.BytesIO(pdf_bytes()), 'sample.pdf'), 'format': format, 'dpi': '150'})
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert f'sample.{format}' in response.headers['Content-Disposition']
    with Image.open(io.BytesIO(response.data)) as image:
        assert image.format.lower() == format
        assert image.size == (150, 150)
        assert image.convert('RGB').getpixel((0, 0)) == (255, 255, 255)


def test_pdf_zip_and_limits():
    result, extension = convert_pdf(pdf_bytes(2), 'png', 72)
    assert extension == 'zip'
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        assert archive.namelist() == ['page-001.png', 'page-002.png']
        for name in archive.namelist():
            with Image.open(io.BytesIO(archive.read(name))) as image:
                assert image.size == (72, 72)
    for data in [pdf_bytes(41), pdf_bytes(width=1000000), b'%PDF-broken', b'not pdf']:
        with pytest.raises(ConversionError):
            convert_pdf(data, 'png', 300)


CSV = b'code,name,value\r\n001,"A & B, Inc.",=1+1\r\n002,"two\nlines",<hello>\r\n'


@pytest.mark.parametrize('format', ['json', 'xml', 'xlsx', 'tsv'])
def test_csv_downloads(client, format):
    response = client.post('/tools/csv-converter', data={
        'file': (io.BytesIO(CSV), 'sample.csv'), 'format': format, 'headers': 'on', 'delimiter': ','})
    assert response.status_code == 200
    assert f'sample.{format}' in response.headers['Content-Disposition']
    if format == 'json':
        rows = json.loads(response.data)
        assert rows[0] == {'code': '001', 'name': 'A & B, Inc.', 'value': '=1+1'}
        assert rows[1]['name'] == 'two\nlines'
    elif format == 'xml':
        root = ET.fromstring(response.data)
        assert root[0][1].text == 'A & B, Inc.'
        assert root[0][1].attrib == {'name': 'name'}
    elif format == 'xlsx':
        book = load_workbook(io.BytesIO(response.data))
        assert book.active['A2'].value == '001'
        assert book.active['C2'].value == '=1+1'
        assert book.active['C2'].data_type == 's'
        book.close()
    else:
        assert "'=1+1" in response.data.decode('utf-8-sig')


def test_csv_headerless_and_bom():
    result = convert_csv(b'\xef\xbb\xbf001;hello\n002;world', 'json', ';', False)
    assert json.loads(result)[0] == {'column_1': '001', 'column_2': 'hello'}


@pytest.mark.parametrize('data', [b'', b'a,a\n1,2', b'a,\n1,2', b'a,b\n1',
                                  b'a\n"unterminated', b'\xff', b'a\n\x00',
                                  b'a\n' + b'x' * 32768,
                                  (','.join(['a'] * 101)).encode()])
def test_invalid_csv(data):
    with pytest.raises(ConversionError):
        convert_csv(data, 'json', ',', True)


def test_errors_are_actionable(client):
    response = client.post('/tools/csv-converter', data={
        'file': (io.BytesIO(b'a,b\n1'), 'sample.csv'), 'format': 'json', 'headers': 'on'})
    assert response.status_code == 400
    assert b'different number of columns' in response.data
    response = client.post('/tools/pdf-to-image', headers={'Accept': 'application/json'})
    assert response.status_code == 400
    assert response.json == {'error': 'Choose a file to convert.'}
    response = client.post('/tools/pdf-to-image', data={
        'file': (io.BytesIO(b'a' * (10 * 1024 * 1024 + 1)), 'big.pdf'), 'format': 'png'})
    assert response.status_code == 400
    assert b'10 MiB' in response.data


def test_csrf_required_and_valid_token_works():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
    client = app.test_client()
    assert client.post('/tools/csv-converter').status_code == 400
    page = client.get('/tools/csv-converter').get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page)[1]
    response = client.post('/tools/csv-converter', data={
        'csrf_token': token, 'file': (io.BytesIO(b'a\n001'), 'sample.csv'),
        'format': 'json', 'headers': 'on'})
    assert response.status_code == 200
    assert response.json == [{'a': '001'}]


def test_pdf_preserves_page_content():
    source = io.BytesIO()
    with Image.new('RGB', (72, 72), (200, 30, 40)) as image:
        image.save(source, format='PDF')
    result, _ = convert_pdf(source.getvalue(), 'png', 72)
    with Image.open(io.BytesIO(result)) as image:
        red, green, blue = image.getpixel((36, 36))
        assert red > 190 and green < 40 and blue < 50


@pytest.mark.parametrize('format,delimiter', [('bad', ','), ('json', 'bad')])
def test_rejects_unknown_csv_options(format, delimiter):
    with pytest.raises(ConversionError):
        convert_csv(b'a\n1', format, delimiter, True)


def test_csv_row_and_cell_limits():
    with pytest.raises(ConversionError, match='50,000'):
        convert_csv(b'a\n' * 50002, 'json', ',', False)
    with pytest.raises(ConversionError, match='200,000'):
        convert_csv(b'a,b,c,d,e\n' * 40001, 'json', ',', False)
