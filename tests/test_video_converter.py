from authentic_dynamics import create_app


def test_video_converter_is_public_get_only_and_restricts_network():
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "WTF_CSRF_ENABLED": False,
                      "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    client = app.test_client()
    response = client.get('/tools/video-converter')
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert '<form' not in page
    assert 'accept="video/*"' in page
    assert 'video-converter.js' in page
    assert 'ffmpeg-core' not in page  # Engine is not eagerly downloaded.
    assert "connect-src 'self'" in response.headers['Content-Security-Policy']
    assert "form-action 'none'" in response.headers['Content-Security-Policy']
    assert 'Cross-Origin-Embedder-Policy' not in response.headers
    assert client.post('/tools/video-converter').status_code == 405
    assert '/tools/video-converter' in client.get('/tools').get_data(as_text=True)
    assert '/tools/video-converter' in client.get('/sitemap.xml').get_data(as_text=True)
    assert 'Content-Security-Policy' not in client.get('/').headers
    asset = client.get('/static/tools/video-converter/ffmpeg/ffmpeg-core.wasm')
    assert asset.status_code == 200
    assert asset.mimetype == 'application/wasm'
    assert asset.data[:4] == b'\x00asm'
