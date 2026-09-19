from authentic_dynamics import create_app


def test_browser_xray_public_page_and_assets():
    app = create_app({"TESTING": True, "SECRET_KEY": "test",
                      "SQLALCHEMY_DATABASE_URI": "sqlite://", "WTF_CSRF_ENABLED": False})
    client = app.test_client()
    response = client.get('/browser-xray')
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '<title>Browser X-Ray | Authentic Dynamics</title>' in page
    assert '<form' not in page
    assert 'aria-current="page"' not in page
    assert 'type="module" src="/static/js/browser-xray.js"' in page
    for key in ('motion', 'location', 'camera', 'microphone', 'screen'):
        assert f'data-confirm="{key}"' in page
        assert f'data-stop="{key}"' in page
        assert f'id="{key}-boundary" hidden' in page
    for asset in ('js/browser-xray.js', 'css/browser-xray.css', 'js/site.js'):
        assert client.get(f'/static/{asset}').status_code == 200
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert client.post('/browser-xray').status_code == 405
