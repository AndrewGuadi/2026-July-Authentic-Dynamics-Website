import csv
import io
import json
import re

import pytest
from openpyxl import load_workbook

from authentic_dynamics import create_app
from authentic_dynamics.blueprints.tools.converters import ConversionError, convert_json


@pytest.fixture
def client():
    return create_app({'TESTING': True, 'SECRET_KEY': 'test', 'WTF_CSRF_ENABLED': False,
                       'SQLALCHEMY_DATABASE_URI': 'sqlite://'}).test_client()


SOURCE = '[{"code":"001","nested":{"city":"Montréal"},"formula":"=1+1"},{"active":true}]'


@pytest.mark.parametrize('output_format', ['xlsx', 'csv', 'tsv', 'json'])
@pytest.mark.parametrize('source', ['upload', 'text'])
def test_json_downloads(client, output_format, source):
    data = {'format': output_format}
    if source == 'upload':
        data['file'] = (io.BytesIO(SOURCE.encode()), 'sample.json')
    else:
        data['json_text'] = SOURCE
    response = client.post('/tools/json-converter', data=data)
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    name = 'sample' if source == 'upload' else 'converted'
    assert f'{name}.{output_format}' in response.headers['Content-Disposition']
    if output_format == 'json':
        assert json.loads(response.data) == json.loads(SOURCE)
    elif output_format == 'xlsx':
        book = load_workbook(io.BytesIO(response.data))
        assert list(book.active.values) == [
            ('code', 'nested', 'formula', 'active'),
            ('001', '{"city": "Montréal"}', '=1+1', None),
            (None, None, None, 'true')]
        assert book.active['C2'].data_type == 's'
        book.close()
    else:
        rows = list(csv.reader(io.StringIO(response.data.decode('utf-8-sig')),
                               delimiter=',' if output_format == 'csv' else '\t'))
        assert rows[1] == ['001', '{"city": "Montréal"}', "'=1+1", '']
        assert rows[2] == ['', '', '', 'true']


@pytest.mark.parametrize('data', [b'{', b'{"a":1,"a":2}', b'NaN', b'1e999',
                                  b'"\\ud800"', b'\xff', b'', b'[' * 2000])
def test_invalid_json(data):
    with pytest.raises(ConversionError):
        convert_json(data, 'json')


@pytest.mark.parametrize('data', [b'[]', b'{}', b'null', b'[1,2]', b'[{"a":1},2]',
                                  b'{"a":"\\u0000"}'])
def test_invalid_spreadsheet_shape(data):
    with pytest.raises(ConversionError):
        convert_json(data, 'xlsx')


def test_json_limits_and_options():
    for value in [[{}] * 50001, {str(i): i for i in range(101)},
                  {'a': 'x' * 32768}, [{'a': 1, 'b': 2, 'c': 3, 'd': 4}] * 50000]:
        with pytest.raises(ConversionError):
            convert_json(json.dumps(value).encode(), 'xlsx')
    with pytest.raises(ConversionError):
        convert_json(b' ' * (10 * 1024 * 1024 + 1), 'json')
    with pytest.raises(ConversionError):
        convert_json(b'{}', 'exe')
    assert json.loads(convert_json(b'\xef\xbb\xbf[1,null,"text"]', 'json')) == [1, None, 'text']
    assert convert_json(b'{"a":null,"b":[1,2]}', 'csv').decode('utf-8-sig') == 'a,b\r\n,"[1, 2]"\r\n'


def test_input_errors_and_page(client):
    page = client.get('/tools/json-converter')
    assert page.status_code == 200
    assert b'name="json_text"' in page.data
    assert b'/tools/json-converter' in client.get('/tools').data
    for data in [{}, {'json_text': '{'}, {'json_text': 'x' * 400001},
                 {'file': (io.BytesIO(b'{}'), 'bad.txt')},
                 {'file': (io.BytesIO(b'{}'), 'ok.json'), 'json_text': '{}'}]:
        response = client.post('/tools/json-converter', data=data,
                               headers={'Accept': 'application/json'})
        assert response.status_code == 400
        assert response.json['error']
    response = client.post('/tools/json-converter', data={'json_text': '<script>'})
    assert response.status_code == 400
    assert b'&lt;script&gt;' in response.data


def test_json_csrf():
    client = create_app({'TESTING': True, 'SECRET_KEY': 'test',
                         'SQLALCHEMY_DATABASE_URI': 'sqlite://'}).test_client()
    assert client.post('/tools/json-converter', data={'json_text': '{}'}).status_code == 400
    page = client.get('/tools/json-converter').get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page)[1]
    response = client.post('/tools/json-converter', data={
        'csrf_token': token, 'json_text': '{"name":"Alex"}', 'format': 'csv'})
    assert response.status_code == 200
