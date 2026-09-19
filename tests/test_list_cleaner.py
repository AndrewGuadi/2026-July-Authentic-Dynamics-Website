from authentic_dynamics import create_app


def test_list_cleaner_page_and_catalog():
    client = create_app({"TESTING": True, "SECRET_KEY": "test",
                         "SQLALCHEMY_DATABASE_URI": "sqlite://",
                         "WTF_CSRF_ENABLED": False}).test_client()
    page = client.get('/tools/list-cleaner')
    assert page.status_code == 200
    assert b'List Cleaner' in page.data
    assert b'<form' not in page.data
    assert b'maxlength="100000"' in page.data
    assert b'js/list-cleaner.js' in page.data
    assert client.get('/static/js/list-cleaner.js').status_code == 200
    assert b'href="/tools/list-cleaner"' in client.get('/tools').data
    assert client.post('/tools/list-cleaner').status_code == 405
