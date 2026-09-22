"""Bounded native conversions; no filenames or media details are logged."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from threading import BoundedSemaphore

import imageio_ffmpeg

from .converters import ConversionError

SLOT = BoundedSemaphore(1)  # One native encoder per WSGI process; do not queue requests.
OUTPUT_LIMIT = 128 * 1024 * 1024
MIMES = {"mp4": "video/mp4", "webm": "video/webm", "mp3": "audio/mpeg", "wav": "audio/wav"}
DEMUXERS = "mov,matroska,webm,avi,mpeg,mpegts"


def inspect_source(executable, source, max_seconds):
    """Inspect container duration and HDR transfer before choosing video filters."""
    try:
        probe = subprocess.run(
            [executable, "-hide_banner", "-nostdin", "-protocol_whitelist", "file",
             "-format_whitelist", DEMUXERS, "-i", str(source)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            timeout=10, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ConversionError("Could not inspect this video. Try a different file.") from exc
    info = probe.stderr
    duration = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", info)
    if not duration or "Video:" not in info:
        raise ConversionError("Could not read this video's duration or video track.")
    seconds = int(duration[1]) * 3600 + int(duration[2]) * 60 + float(duration[3])
    if seconds > max_seconds:
        raise ConversionError(f"Server videos must be {max_seconds // 60} minutes or shorter.")
    return bool(re.search(r"smpte2084|arib-std-b67", info, re.IGNORECASE))


def arguments(options, hdr=False, max_seconds=180):
    choices = {"format": MIMES, "quality": ("smaller", "balanced", "higher"),
               "resolution": ("original", "1080", "720", "480"),
               "fps": ("original", "60", "30", "24"), "audio": ("keep", "remove")}
    if any(options.get(key) not in values for key, values in choices.items()):
        raise ConversionError("Choose valid conversion settings.")
    fmt, quality = options["format"], options["quality"]
    # Disallow network access, playlists and arbitrary demuxers. Never use a shell.
    args = ["-nostdin", "-y", "-v", "error", "-max_alloc", "134217728",
            "-threads", "2", "-filter_threads", "1", "-protocol_whitelist", "file",
            "-format_whitelist", DEMUXERS, "-autorotate", "-i", "input",
            "-map_metadata", "-1"]
    if fmt in ("mp3", "wav"):
        args += ["-map", "0:a:0", "-vn", "-c:a", "libmp3lame" if fmt == "mp3" else "pcm_s16le"]
        if fmt == "mp3":
            args += ["-b:a", {"smaller": "96k", "balanced": "160k", "higher": "256k"}[quality]]
    else:
        args += ["-map", "0:v:0"]
        args += ["-map", "0:a:0?"] if options["audio"] == "keep" else ["-an"]
        scale = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        if options["resolution"] != "original":
            short = int(options["resolution"])
            long = round(short * 16 / 9)
            scale = (f"scale=w='min(iw,if(gte(iw,ih),{long},{short}))':"
                     f"h='min(ih,if(gte(iw,ih),{short},{long}))':"
                     "force_original_aspect_ratio=decrease:force_divisible_by=2")
        if hdr:
            # Map PQ/HLG wide-gamut footage into displayable SDR BT.709.
            scale = ("zscale=t=linear:npl=100,format=gbrpf32le,"
                     "tonemap=tonemap=hable:desat=0,"
                     "zscale=p=bt709:t=bt709:m=bt709:r=tv," + scale)
        args += ["-vf", scale, "-pix_fmt", "yuv420p", "-threads", "2"]
        if hdr:
            args += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
        if options["fps"] != "original":
            args += ["-r", options["fps"]]
        if fmt == "mp4":
            args += ["-c:v", "libx264", "-crf", {"smaller": "30", "balanced": "23", "higher": "18"}[quality],
                     "-preset", "veryfast", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k"]
        else:
            args += ["-c:v", "libvpx", "-crf", {"smaller": "35", "balanced": "20", "higher": "10"}[quality],
                     "-b:v", {"smaller": "600k", "balanced": "1500k", "higher": "3000k"}[quality],
                     "-deadline", "realtime", "-cpu-used", "6", "-lag-in-frames", "0",
                     "-c:a", "libopus", "-b:a", "96k"]
    return args + ["-t", str(max_seconds), "-fs", str(OUTPUT_LIMIT), "output." + fmt]


def convert(upload, options, max_bytes, timeout, max_seconds=180):
    arguments(options)  # Reject untrusted settings before reading a file.
    if not SLOT.acquire(blocking=False):
        raise ConversionError("The server is busy. Try again shortly or choose browser conversion.")
    result = None
    try:
        with tempfile.TemporaryDirectory(prefix="ad-video-") as directory:
            source = Path(directory) / "input"
            total = 0
            with source.open("wb") as target:
                while chunk := upload.stream.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ConversionError("This video exceeds the server file-size limit. Use browser conversion.")
                    target.write(chunk)
            if not total:
                raise ConversionError("Choose a nonempty video file.")
            executable = imageio_ffmpeg.get_ffmpeg_exe()
            hdr = inspect_source(executable, source, max_seconds)
            args = arguments(options, hdr=hdr, max_seconds=max_seconds)
            subprocess.run([executable, *args], cwd=directory,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=timeout, check=True)
            output = Path(directory) / ("output." + options["format"])
            if not output.is_file() or not 0 < output.stat().st_size < OUTPUT_LIMIT:
                raise ConversionError("The converted file exceeds the 128 MB server output limit. Use browser conversion.")
            result = tempfile.TemporaryFile()  # noqa: SIM115 -- response owns and closes this file
            with output.open("rb") as encoded:
                shutil.copyfileobj(encoded, result)
            result.seek(0)
        return result
    except subprocess.TimeoutExpired as exc:
        raise ConversionError("Server conversion took too long. Try a shorter video or browser conversion.") from exc
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        if result:
            result.close()
        raise ConversionError("Server conversion failed. Try another format or video. Audio extraction needs an audio track.") from exc
    finally:
        SLOT.release()
