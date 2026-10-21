"""Human-facing Hub forms retain input and preserve domain/API semantics."""
from urllib.parse import parse_qs, urlsplit

import test_hub as baseline
from test_hub import business, csrf, mutate, project

app = baseline.app
client = baseline.client


def submit(client, path, values):
    return client.post(path, data={'csrf_token': csrf(client, path), '_hub_units': 'major', **values})


def test_money_form_uses_major_units_without_changing_api(client):
    company = business(client)
    path = '/hub/payments/new'
    page = client.get(path).text
    assert 'Enter cents' not in page
    assert 'name="amount_minor"' in page and 'step="0.01"' in page
    result = submit(client, path, {'business_id': company['id'], 'amount_minor': '123.45',
                                'received_on': '2026-10-20', 'method': 'check'})
    assert result.status_code == 303, result.text
    record_id = urlsplit(result.location).path.rsplit('/', 1)[1]
    assert client.get(f'/hub/api/payments/{record_id}').json['amount_minor'] == 12345
    detail = client.get(result.location).text
    assert '123.45' in detail and 'Amount Minor' not in detail
    assert 'value="123.45"' in client.get(f'/hub/payments/{record_id}/edit').text


def test_money_errors_preserve_input_and_link_to_field(client):
    company = business(client)
    result = submit(client, '/hub/payments/new', {'business_id': company['id'],
                    'amount_minor': '1.234', 'received_on': '2026-10-20', 'method': 'check'})
    assert result.status_code == 400
    assert 'value="1.234"' in result.text
    assert 'href="#field-amount_minor"' in result.text
    assert 'aria-invalid="true"' in result.text
    assert 'Your changes have not been saved.' in result.text
    assert client.get('/hub/api/payments').json['total'] == 0


def test_workspace_time_round_trip_and_dst_validation(client):
    delivery = project(client)
    path = '/hub/tasks/new'
    response = submit(client, path, {'project_id': delivery['id'], 'title': 'Customer call',
                                   'due_at': '2026-10-20T14:30'})
    assert response.status_code == 303, response.text
    record_id = urlsplit(response.location).path.rsplit('/', 1)[1]
    assert client.get(f'/hub/api/tasks/{record_id}').json['due_at'] == '2026-10-20T18:30:00+00:00'
    page = client.get(f'/hub/tasks/{record_id}/edit').text
    assert 'type="datetime-local"' in page
    assert 'America/New_York' in page and '2026-10-20T14:30:00' in page
    for date, message in [('2026-03-08T02:30', 'does not exist'),
                          ('2026-11-01T01:30', 'occurs twice')]:
        result = submit(client, path, {'project_id': delivery['id'], 'title': 'Clock change', 'due_at': date})
        assert result.status_code == 400
        assert message in result.text


def test_domain_error_is_inline_and_retains_entries(client):
    company = business(client)
    values = {'business_id': company['id'], 'invoice_number': 'AD-SAME',
              'issue_date': '2026-10-20', 'due_date': '2026-11-20'}
    mutate(client, 'invoices', values)
    result = submit(client, '/hub/invoices/new', values)
    assert result.status_code == 400
    assert 'value="AD-SAME"' in result.text
    assert 'Your changes have not been saved.' in result.text
    assert '<form class="hub-panel hub-form"' in result.text


def test_scoped_list_context_survives_navigation(client):
    delivery = project(client)
    first = None
    for index in range(31):
        task = mutate(client, 'tasks', {'project_id': delivery['id'], 'title': f'Task {index}'})
        first = first or task
    scope = f'project_id={delivery["id"]}&q=Task'
    page = client.get('/hub/tasks?' + scope).text
    assert f'project_id={delivery["id"]}' in page
    assert 'page=2' in page
    assert f'name="project_id" value="{delivery["id"]}"' in page
    result = submit(client, '/hub/tasks/new?' + scope, {'project_id': delivery['id'], 'title': 'Task new'})
    assert result.status_code == 303
    assert parse_qs(urlsplit(result.location).query) == {'project_id': [delivery['id']], 'q': ['Task']}
    detail = client.get(result.location).text
    assert 'q=Task' in detail


def test_completed_tasks_do_not_count_as_open(client):
    delivery = project(client)
    mutate(client, 'tasks', {'project_id': delivery['id'], 'title': 'Finished', 'status': 'done'})
    page = client.get('/hub').text
    assert '<span>Open tasks</span><strong>0</strong>' in page


def test_audit_displays_actor_and_human_stage_names(client):
    company = business(client)
    stages = client.get('/hub/api/pipeline_stages').json['items']
    same = [stage for stage in stages if stage['pipeline_id'] == stages[0]['pipeline_id']]
    first, second = same[:2]
    item = mutate(client, 'opportunities', {'business_id': company['id'], 'pipeline_id': first['pipeline_id'],
                   'stage_id': first['id'], 'title': 'Customer website'})
    mutate(client, 'opportunities', {'stage_id': second['id']}, item['id'])
    page = client.get(f'/hub/opportunities/{item["id"]}').text
    assert 'By ' in page and first['name'] in page and second['name'] in page


def test_invalid_money_url_prefills_are_ignored(client):
    for value in ['bad', 'NaN', 'Infinity', '-1', '99999999999999999999999999', '1.5']:
        result = client.get('/hub/payments/new', query_string={'amount_minor': value})
        assert result.status_code == 200
        assert f'value="{value}"' not in result.text
    assert 'value="123.45"' in client.get('/hub/payments/new?amount_minor=12345').text
