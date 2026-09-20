from authentic_dynamics import create_app


def test_qr_maker_is_public_browser_only_and_discoverable():
    client = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"}).test_client()
    page = client.get('/tools/qr-code-maker')
    assert page.status_code == 200
    assert b'id="qr-url"' in page.data
    assert b'<form' not in page.data
    assert client.post('/tools/qr-code-maker').status_code == 405
    assert b'href="/tools/qr-code-maker"' in client.get('/tools').data
    assert b'/tools/qr-code-maker' in client.get('/sitemap.xml').data
    for path in ('js/qr-code-maker.js', 'css/qr-code-maker.css',
                 'vendor/qr/qrcode-2.0.4.mjs'):
        assert client.get(f'/static/{path}').status_code == 200
