import base64
import io
import json
from pathlib import Path

from flask import current_app, make_response, render_template, request, send_file
from werkzeug.utils import secure_filename

from . import bp, video_backend
from .converters import MAX_FILE_BYTES, ConversionError, convert_csv, convert_json, convert_pdf
from .pdf_tables import render_pdf_page

MIMETYPES = {
    "png": "image/png", "webp": "image/webp", "jpeg": "image/jpeg",
    "zip": "application/zip", "json": "application/json", "xml": "application/xml",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "tsv": "text/tab-separated-values",
    "csv": "text/csv",
    "txt": "text/plain; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("")
@bp.get("/")
def catalog():
    return render_template("tools/catalog.html", active_page="tools")


@bp.route("/pdf-to-image", methods=["GET", "POST"])
def pdf():
    return converter("pdf")


@bp.get("/local-ai")
def local_ai():
    return render_template("tools/local_ai.html", active_page="tools")


@bp.get("/video-converter")
def video_converter():
    response = make_response(render_template(
        "tools/video_converter.html", active_page="tools",
        server_enabled=current_app.config["VIDEO_SERVER_ENABLED"],
        server_max_bytes=current_app.config["VIDEO_MAX_BYTES"],
        server_timeout=current_app.config["VIDEO_TIMEOUT_SECONDS"],
    ))
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; "
        "style-src 'self'; img-src 'self' data:; font-src 'self'; "
        "media-src blob:; worker-src 'self'; connect-src 'self'; "
        "form-action 'none'; base-uri 'none'; frame-ancestors 'self'"
    )
    return response


@bp.post("/video-converter/convert")
def video_server():
    if not current_app.config["VIDEO_SERVER_ENABLED"]:
        return {"error": "Server conversion is unavailable. Choose browser conversion."}, 503
    if request.headers.get("X-Video-Upload-Consent") != "yes":
        return {"error": "Agree to upload your video before using server conversion."}, 400
    try:
        upload = request.files.get("file")
        if upload is None or len(request.files) != 1:
            raise ConversionError("Choose one video file.")
        options = {key: request.form.get(key) for key in
                   ("format", "quality", "resolution", "fps", "audio")}
        result = video_backend.convert(upload, options, current_app.config["VIDEO_MAX_BYTES"],
                                       current_app.config["VIDEO_TIMEOUT_SECONDS"])
        response = send_file(result, mimetype=video_backend.MIMES[options["format"]],
                             as_attachment=True, download_name="converted." + options["format"],
                             max_age=0)
        response.direct_passthrough = False
        response.call_on_close(result.close)
        return response
    except ConversionError as exc:
        return {"error": str(exc)}, 400


@bp.get("/list-cleaner")
def list_cleaner():
    return render_template("tools/list_cleaner.html", active_page="tools")


@bp.get("/free-invoice-maker")
def free_invoice_maker():
    return render_template("tools/free_invoice_maker.html", active_page="tools")


@bp.get("/qr-code-maker")
def qr_code_maker():
    return render_template("tools/qr_code_maker.html", active_page="tools")


@bp.route("/csv-converter", methods=["GET", "POST"])
def csv():
    return converter("csv")


@bp.route("/json-converter", methods=["GET", "POST"])
def json_converter():
    error = None
    preview = None
    if request.method == "POST":
        try:
            upload = request.files.get("file")
            content = request.form.get("json_text", "")
            stem = "converted"
            if upload and upload.filename:
                if content.strip():
                    raise ConversionError("Choose either a file or pasted JSON, then clear the other input.")
                if Path(upload.filename).suffix.lower() != ".json":
                    raise ConversionError("Choose a .json file.")
                data = upload.read(MAX_FILE_BYTES + 1)
                stem = Path(secure_filename(upload.filename)).stem[:100] or "converted"
            else:
                data = content.encode("utf-8")
                if len(data) > 400000:
                    raise ConversionError("Pasted JSON is limited to 400 KB. Upload a JSON file for larger data.")
            extension = request.form.get("format", "xlsx")
            depth = request.form.get("max_depth", "5") if extension == "xlsx" else "5"
            if depth not in {str(number) for number in range(1, 11)}:
                raise ConversionError("Choose a nesting depth from 1 to 10.")
            is_preview = request.form.get("action") in {"preview", "pdf_preview"}
            pdf_options = None
            if extension == "pdf":
                size = request.form.get("pdf_font_size", "10")
                if size not in {"10", "11", "12"}:
                    raise ConversionError("Choose a PDF text size from 10 to 12 pt.")
                try:
                    columns = json.loads(request.form["pdf_columns"]) if request.form.get("pdf_columns") else None
                except (ValueError, RecursionError) as exc:
                    raise ConversionError("Choose valid PDF columns.") from exc
                pdf_options = {"orientation": request.form.get("pdf_orientation", "auto"),
                               "font_size": int(size), "columns": columns,
                               "long_cells": request.form.get("pdf_long_cells", "wrap")}
            result = convert_json(data, extension, request.form.get("nesting", "combined"),
                                  int(depth), preview=is_preview, pdf_options=pdf_options)
            if is_preview and extension == "pdf":
                if request.accept_mimetypes.best == "application/json":
                    return {"pdf": base64.b64encode(result["pdf"]).decode("ascii"),
                            "image": base64.b64encode(render_pdf_page(result["pdf"])).decode("ascii"),
                            "filename": f"{stem}.pdf", "summary": result["summary"]}
                return send_file(io.BytesIO(result["pdf"]), mimetype="application/pdf",
                                 download_name=f"{stem}.pdf", max_age=0)
            if is_preview:
                preview = result
                if request.accept_mimetypes.best == "application/json":
                    return preview
            else:
                return send_file(io.BytesIO(result), mimetype=MIMETYPES[extension],
                                 as_attachment=True, download_name=f"{stem}.{extension}", max_age=0)
        except ConversionError as exc:
            error = str(exc)
            if request.accept_mimetypes.best == "application/json":
                return {"error": error}, 400
    return render_template("tools/json_converter.html", error=error, preview=preview,
                           values=request.form, active_page="tools"), 400 if error else 200


@bp.post("/json-converter/pdf-page")
def json_pdf_page():
    try:
        upload = request.files.get("file")
        page = request.form.get("page", "0")
        if not upload or not page.isascii() or not page.isdigit() or len(page) > 3:
            raise ConversionError("Choose a valid PDF preview page.")
        result = render_pdf_page(upload.read(MAX_FILE_BYTES + 1), int(page))
        return send_file(io.BytesIO(result), mimetype="image/png", max_age=0)
    except ConversionError as exc:
        return {"error": str(exc)}, 400


def converter(kind):
    error = None
    if request.method == "POST":
        try:
            upload = request.files.get("file")
            if not upload or not upload.filename:
                raise ConversionError("Choose a file to convert.")
            if Path(upload.filename).suffix.lower() != f".{kind}":
                raise ConversionError(f"Choose a .{kind} file.")
            data = upload.read(MAX_FILE_BYTES + 1)
            if not data or len(data) > MAX_FILE_BYTES:
                raise ConversionError("Choose a nonempty file no larger than 10 MiB.")
            extension = request.form.get("format", "")
            if kind == "pdf":
                dpi = request.form.get("dpi", "150")
                if dpi not in {"72", "150", "300"}:
                    raise ConversionError("Choose a supported resolution.")
                result, extension = convert_pdf(data, extension, int(dpi))
            else:
                result = convert_csv(data, extension, request.form.get("delimiter", ","),
                                     request.form.get("headers") == "on")
            stem = Path(secure_filename(upload.filename)).stem[:100] or "converted"
            return send_file(io.BytesIO(result), mimetype=MIMETYPES[extension],
                             as_attachment=True, download_name=f"{stem}.{extension}", max_age=0)
        except ConversionError as exc:
            error = str(exc)
            if request.accept_mimetypes.best == "application/json":
                return {"error": error}, 400
    return render_template("tools/converter.html", kind=kind, error=error,
                           values=request.form, active_page="tools"), 400 if error else 200
