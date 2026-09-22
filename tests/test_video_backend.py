import io
import re
import subprocess

import imageio_ffmpeg
import pytest

from authentic_dynamics import create_app
from authentic_dynamics.blueprints.tools import video_backend


@pytest.fixture
def app():
    return create_app({"TESTING": True, "SECRET_KEY": "test", "WTF_CSRF_ENABLED": False,
                       "SQLALCHEMY_DATABASE_URI": "sqlite://"})


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    path = tmp_path_factory.mktemp("native-video") / "input.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=320x180:rate=24", "-f", "lavfi", "-i", "sine=frequency=440",
                    "-t", "0.5", "-c:v", "libx264", "-c:a", "aac", str(path)], check=True)
    return path.read_bytes()


def post(client, video, **options):
    data = {"file": (io.BytesIO(video), "private-name.mp4"), "format": "mp4", "quality": "balanced",
            "resolution": "original", "fps": "original", "audio": "keep", **options}
    return client.post('/tools/video-converter/convert', data=data,
                       headers={"X-Video-Upload-Consent": "yes"})


@pytest.mark.parametrize("fmt,codec", [("mp4", "h264"), ("webm", "vp8"), ("mp3", "mp3"), ("wav", "pcm_s16le")])
def test_real_native_conversion(app, video, tmp_path, fmt, codec):
    response = post(app.test_client(), video, format=fmt)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert "private-name" not in str(response.headers)
    output = tmp_path / ("output." + fmt)
    output.write_bytes(response.data)
    response.close()
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(output),
                             "-f", "null", "-"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert codec in result.stderr


def test_consent_limits_disabled_invalid_and_corrupt(app, video):
    client = app.test_client()
    assert client.post('/tools/video-converter/convert').status_code == 400
    assert post(client, video, format="../../bad").status_code == 400
    assert post(client, b"corrupt").status_code == 400
    app.config["VIDEO_MAX_BYTES"] = 20
    assert post(client, video).status_code == 400
    app.config["VIDEO_SERVER_ENABLED"] = False
    assert post(client, video).status_code == 503


def test_timeout_cleanup_and_busy(app, video, monkeypatch, tmp_path):
    monkeypatch.setattr(video_backend.tempfile, "tempdir", str(tmp_path))
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("ffmpeg", 1)
    monkeypatch.setattr(video_backend.subprocess, "run", timeout)
    result = post(app.test_client(), video)
    assert "inspect" in result.json["error"]
    assert not list(tmp_path.iterdir())
    with video_backend.SLOT:
        assert "busy" in post(app.test_client(), video).json["error"]


def test_csrf_and_video_only_request_limit(app, video):
    app.config.update(WTF_CSRF_ENABLED=True, MAX_CONTENT_LENGTH=1000)
    client = app.test_client()
    assert post(client, video).status_code == 400
    page = client.get('/tools/video-converter').text
    token = re.search(r'name="csrf-token" content="([^"]+)"', page)[1]
    response = client.post('/tools/video-converter/convert', data={
        "file": (io.BytesIO(video), "input.mp4"), "format": "mp4", "quality": "balanced",
        "resolution": "original", "fps": "original", "audio": "remove",
    }, headers={"X-CSRFToken": token, "X-Video-Upload-Consent": "yes"})
    assert response.status_code == 200
    response.close()
    assert client.post('/tools/csv-converter', data={"file": (io.BytesIO(video), "x.csv")}).status_code == 413


def make_mov(tmp_path, codec, *, hdr_transfer=None, rotation=False):
    path = tmp_path / ("source-" + codec + ".mov")
    args = [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=size=320x180:rate=24", "-t", "0.5", "-threads", "1"]
    if hdr_transfer:
        args += ["-vf", "format=yuv420p10le", "-c:v", "libx265", "-x265-params",
                 "pools=1:frame-threads=1:log-level=error", "-color_primaries", "bt2020",
                 "-color_trc", hdr_transfer, "-colorspace", "bt2020nc"]
    else:
        args += ["-c:v", codec]
    subprocess.run([*args, str(path)], check=True, capture_output=True)
    if rotation:
        turned = tmp_path / "rotated.mov"
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-display_rotation",
                        "90", "-i", str(path), "-c", "copy", str(turned)],
                       check=True, capture_output=True)
        path = turned
    return path.read_bytes()


@pytest.mark.parametrize("codec,transfer,rotation,dimensions", [
    ("libx265", None, False, "320x180"),
    ("libx265", "smpte2084", False, "320x180"),
    ("libx265", "arib-std-b67", False, "320x180"),
    ("libx264", None, True, "180x320"),
    ("prores_ks", None, False, "320x180"),
])
def test_iphone_style_mov_to_sdr_mp4(app, tmp_path, codec, transfer, rotation, dimensions):
    source = make_mov(tmp_path, codec, hdr_transfer=transfer, rotation=rotation)
    response = post(app.test_client(), source)
    assert response.status_code == 200, response.json
    output = tmp_path / "converted.mp4"
    output.write_bytes(response.data)
    response.close()
    details = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(output)],
                             capture_output=True, text=True, check=False).stderr
    assert "Video: h264" in details
    assert dimensions in details
    if transfer:
        assert "bt709" in details
        assert transfer not in details


def test_server_duration_limit(app, video):
    app.config["VIDEO_MAX_SECONDS"] = 0
    response = post(app.test_client(), video)
    assert response.status_code == 400
    assert "minutes or shorter" in response.json["error"]


def test_default_video_limits(app):
    assert app.config["VIDEO_MAX_BYTES"] == 128 * 1024 * 1024
    assert app.config["VIDEO_MAX_SECONDS"] == 180
    assert app.config["VIDEO_TIMEOUT_SECONDS"] == 300
    assert app.config["VIDEO_BROWSER_MAX_BYTES"] == 64 * 1024 * 1024
    assert app.config["VIDEO_BROWSER_MAX_SECONDS"] == 60
