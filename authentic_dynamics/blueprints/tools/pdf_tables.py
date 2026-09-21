"""Measured, bounded PDF tables. Plans are validated before drawing any content."""

import io
import json
import math
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from .conversion_errors import ConversionError

PDF_LOCK = threading.Lock()  # All PDFium access, including existing image conversions.
PDF_WRITE_LOCK = threading.Lock()  # Embedded TrueType font state is not shared concurrently.
FONT = "ADTable"
pdfmetrics.registerFont(TTFont(FONT, str(
    Path(__file__).resolve().parents[2] / "static/fonts/DejaVuSans.ttf")))
MARGIN = 36
TABLE_TOP = 66
BOTTOM_MARGIN = 42
PADDING = 6
MAX_PAGES = 200
MAX_TEXT = 2_000_000
MAX_ROWS = 5000
MAX_BYTES = 10 * 1024 * 1024
LONG_CELL = 1000


@dataclass
class Line:
    text: str
    start: int
    end: int


@dataclass
class Cell:
    x: float
    top: float
    width: float
    height: float
    lines: list
    row: int  # -1 identifies repeated headers.
    column: int


@dataclass
class Page:
    section: int
    cells: list
    labels: list


@dataclass
class Plan:
    pages: list
    sections: list
    width: float
    height: float
    font_size: int
    orientation: str
    continuations: int
    line_count: int


def _display(text, warnings):
    glyphs = pdfmetrics.getFont(FONT).face.charToGlyph
    result = []
    for char in text:
        if char == "\n":
            result.append(char)
        elif (not glyphs.get(ord(char)) or unicodedata.category(char) in {"Cc", "Cf"}
              or unicodedata.bidirectional(char) in {"R", "AL", "AN"}):
            result.append(f"\\u{ord(char):04x}" if ord(char) <= 65535 else f"\\U{ord(char):08x}")
            warnings.add("Unsupported, control, or complex-script characters are shown as Unicode "
                         "escape codes. They have not been silently dropped.")
        else:
            result.append(char)
    return "".join(result)


def _text(value):
    return value if isinstance(value, str) else (
        "" if value is None else json.dumps(value, ensure_ascii=False, allow_nan=False))


def prepare_sections(records, columns=None, long_cells="wrap"):
    headers = list(dict.fromkeys(key for record in records for key in record))
    if columns is not None:
        if (not isinstance(columns, list) or not columns or
                not all(isinstance(key, str) for key in columns) or
                len(set(columns)) != len(columns) or any(key not in headers for key in columns)):
            raise ConversionError("Select at least one valid, unique PDF column.")
        headers = columns
    if not headers or len(headers) > 12:
        raise ConversionError("PDF tables support 1–12 columns. Use Choose columns to select fewer fields.")
    if len(records) > MAX_ROWS:
        raise ConversionError("PDF tables support at most 5,000 rows. Choose Excel or fewer records.")
    if long_cells not in {"wrap", "appendix", "shorten"}:
        raise ConversionError("Choose a supported long-cell option.")
    warnings, appendix, shortened, total = set(), [], 0, 0
    output = []
    for row_number, record in enumerate(records, 1):
        row = []
        for key in headers:
            value = _text(record.get(key))
            total += len(value)
            if total > MAX_TEXT:
                raise ConversionError("PDF tables support up to 2 million characters. Select fewer columns or use JSON.")
            if len(value) > LONG_CELL and long_cells == "appendix":
                reference = f"A{len(appendix) + 1}"
                appendix.append([f"{reference} | Row {row_number} | Field: {key}\n{value}"])
                value = f"See appendix {reference} for the full value."
            elif len(value) > LONG_CELL and long_cells == "shorten":
                shortened += 1
                value = value[:LONG_CELL] + f"\n[SHORTENED: {len(value) - LONG_CELL} characters omitted]"
            row.append(value)
        output.append(row)
    if appendix:
        warnings.add(f"{len(appendix)} long values appear in a linked appendix after the table.")
    if shortened:
        warnings.add(f"You chose shortening: {shortened} values are incomplete and visibly marked SHORTENED.")
    sections = [{"title": "JSON table", "headers": headers, "rows": output}]
    if appendix:
        sections.append({"title": "Long values - appendix", "headers": ["Full values"], "rows": appendix})
    display_size = 0
    for section in sections:
        section["headers"] = [_display(key, warnings) for key in section["headers"]]
        section["rows"] = [[_display(value, warnings) for value in row] for row in section["rows"]]
        display_size += sum(len(value) for row in [section["headers"], *section["rows"]] for value in row)
    if display_size > MAX_TEXT:
        raise ConversionError("The rendered PDF text exceeds 2 million characters. Select fewer columns or use JSON.")
    return sections, warnings, shortened, len(appendix)


def wrap_text(text, width, size):
    """Keep exact source spans, including whitespace and explicit line breaks."""
    widths = pdfmetrics.getFont(FONT).face.charWidths
    result, start = [], 0
    while start < len(text):
        end, used, last_space = start, 0, None
        while end < len(text):
            char = text[end]
            if char == "\n":
                end += 1
                break
            advance = widths[ord(char)] * size / 1000
            if used + advance > width + 0.001:
                if last_space is not None:
                    end = last_space
                break
            used += advance
            end += 1
            if char.isspace():
                last_space = end
        if end == start:
            raise ConversionError("A column is too narrow at this text size. Select fewer columns or landscape.")
        result.append(Line(text[start:end].removesuffix("\n"), start, end))
        start = end
    return result or [Line("", 0, 0)]


def _column_widths(section, usable, size, weighted):
    count = len(section["headers"])
    minimum = max(64, 5 * size + 2 * PADDING)
    if count * minimum > usable:
        raise ConversionError("These columns cannot fit readably. Choose landscape, fewer columns, or a smaller text size.")
    if not weighted:
        return [usable / count] * count
    weights = []
    for index, header in enumerate(section["headers"]):
        sample = [header[:160], *(row[index][:160] for row in section["rows"][:100])]
        measures = sorted(pdfmetrics.stringWidth(value.replace("\n", " "), FONT, size) for value in sample)
        typical = measures[min(len(measures) - 1, int(len(measures) * 0.85))]
        weights.append(math.sqrt(max(1, typical - minimum)))
    remainder = usable - count * minimum
    return [minimum + remainder * weight / sum(weights) for weight in weights]


def _candidate(sections, orientation, size, weighted):
    width, height = landscape(A4) if orientation == "landscape" else A4
    leading = size * 1.45
    pages, continuations, line_count = [], 0, 0
    for section_index, section in enumerate(sections):
        widths = _column_widths(section, width - 2 * MARGIN, size, weighted)
        header_lines = [wrap_text(value, w - 2 * PADDING, size)
                        for value, w in zip(section["headers"], widths)]
        header_height = max(map(len, header_lines)) * leading + 2 * PADDING
        if header_height > (height - TABLE_TOP - BOTTOM_MARGIN) * 0.25:
            raise ConversionError("Column names take too much page space. Shorten the keys or select fewer columns.")

        def cells(lines, top, cell_height, row, widths=widths):
            x, result = MARGIN, []
            for column, (wrapped, column_width) in enumerate(zip(lines, widths)):
                result.append(Cell(x, top, column_width, cell_height, wrapped, row, column))
                x += column_width
            return result

        def new_page(section_index=section_index, header_lines=header_lines,
                     header_height=header_height, cells=cells):
            if len(pages) >= MAX_PAGES:
                raise ConversionError("This PDF exceeds 200 pages. Select fewer columns/rows or move long values to the appendix.")
            page = Page(section_index, cells(header_lines, TABLE_TOP, header_height, -1), [])
            pages.append(page)
            return page, TABLE_TOP + header_height

        page, top = new_page()
        full_body = height - BOTTOM_MARGIN - top
        for row_index, row in enumerate(section["rows"]):
            wrapped = [wrap_text(value, w - 2 * PADDING, size) for value, w in zip(row, widths)]
            line_count += sum(map(len, wrapped))
            count = max(map(len, wrapped))
            row_height = count * leading + 2 * PADDING
            if row_height <= full_body:
                if top + row_height > height - BOTTOM_MARGIN:
                    page, top = new_page()
                page.cells.extend(cells(wrapped, top, row_height, row_index))
                top += row_height
                continue
            offset = 0
            while offset < count:
                available = math.floor((height - BOTTOM_MARGIN - top - leading - 2 * PADDING) / leading)
                if available < 1:
                    page, top = new_page()
                    continue
                take = min(available, count - offset)
                if offset:
                    continuations += 1
                label = f"Row {row_index + 1} - {'continued' if offset else 'continues across pages'}"
                page.labels.append((top, label))
                top += leading
                fragment_height = take * leading + 2 * PADDING
                page.cells.extend(cells([lines[offset:offset + take] for lines in wrapped],
                                        top, fragment_height, row_index))
                top += fragment_height
                offset += take
                if offset < count:
                    page, top = new_page()
    return Plan(pages, sections, width, height, size, orientation, continuations, line_count)


def validate_plan(plan):
    """Reject clipping, overlaps, missing text, and unreadable font sizes at runtime."""
    if plan.font_size < 10:
        raise ConversionError("PDF text must be at least 10 pt.")
    consumed = {}
    for page in plan.pages:
        previous, right_edges = {}, {}
        for cell in page.cells:
            if (cell.x < MARGIN - 0.01 or cell.top < TABLE_TOP - 0.01 or
                    cell.x + cell.width > plan.width - MARGIN + 0.01 or
                    cell.top + cell.height > plan.height - BOTTOM_MARGIN + 0.01 or
                    cell.top < previous.get(cell.column, TABLE_TOP) - 0.01 or
                    cell.x < right_edges.get((cell.top, cell.row), MARGIN) - 0.01 or
                    len(cell.lines) * plan.font_size * 1.45 + 2 * PADDING > cell.height + 0.01):
                raise ConversionError("The PDF layout could not fit safely. Choose fewer columns or another layout.")
            previous[cell.column] = cell.top + cell.height
            right_edges[(cell.top, cell.row)] = cell.x + cell.width
            for line in cell.lines:
                if pdfmetrics.stringWidth(line.text, FONT, plan.font_size) > cell.width - 2 * PADDING + 0.01:
                    raise ConversionError("PDF text would overflow a cell. Choose fewer columns.")
                if cell.row != -1:
                    key = (page.section, cell.row, cell.column)
                    original = plan.sections[page.section]["rows"][cell.row][cell.column]
                    if (line.start != consumed.get(key, 0) or
                            line.text != original[line.start:line.end].removesuffix("\n")):
                        raise ConversionError("The PDF content check failed. Try a different layout.")
                    consumed[key] = line.end
    for section_index, section in enumerate(plan.sections):
        for row_index, row in enumerate(section["rows"]):
            for column, value in enumerate(row):
                if consumed.get((section_index, row_index, column)) != len(value):
                    raise ConversionError("Some content could not be placed in the PDF. Choose another layout.")


def build_pdf(records, orientation="auto", font_size=10, columns=None, long_cells="wrap"):
    with PDF_WRITE_LOCK:
        return _build_pdf(records, orientation, font_size, columns, long_cells)


def _build_pdf(records, orientation, font_size, columns, long_cells):
    if orientation not in {"auto", "portrait", "landscape"} or font_size not in {10, 11, 12}:
        raise ConversionError("Choose a supported PDF orientation and text size (10–12 pt).")
    sections, warnings, shortened, appendix = prepare_sections(records, columns, long_cells)
    candidates, errors = [], []
    for direction in (["portrait", "landscape"] if orientation == "auto" else [orientation]):
        for weighted in [True, False]:
            try:
                candidate = _candidate(sections, direction, font_size, weighted)
                validate_plan(candidate)
                candidates.append(candidate)
            except ConversionError as exc:
                errors.append(exc)
    if not candidates:
        raise errors[-1]
    # Keep size fixed. Prefer fewer split rows and less wrapping before page count.
    plan = min(candidates, key=lambda item: (item.continuations, item.line_count,
                                           len(item.pages), item.orientation != "portrait"))
    if plan.continuations:
        warnings.add("Long rows continue on subsequent pages with row numbers and repeated column headers.")
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(plan.width, plan.height), pageCompression=1, invariant=1)
    canvas.setTitle("JSON table | Authentic Dynamics")
    canvas.setAuthor("Authentic Dynamics")
    ascent, _ = pdfmetrics.getAscentDescent(FONT, font_size)
    for page_index, page in enumerate(plan.pages, 1):
        canvas.setFont(FONT, font_size)
        canvas.setFillColorRGB(0.15, 0.21, 0.11)
        canvas.drawString(MARGIN, plan.height - 34, plan.sections[page.section]["title"])
        for top, label in page.labels:
            canvas.drawString(MARGIN, plan.height - top - ascent, label)
        for cell in page.cells:
            header = cell.row == -1
            canvas.setFillColorRGB(*(0.15, 0.21, 0.11) if header else (1, 1, 1))
            canvas.setStrokeColorRGB(0.65, 0.69, 0.62)
            canvas.setLineWidth(0.4)
            canvas.rect(cell.x, plan.height - cell.top - cell.height, cell.width, cell.height, fill=1)
            canvas.setFillColorRGB(*(1, 1, 1) if header else (0.08, 0.08, 0.08))
            for index, line in enumerate(cell.lines):
                canvas.drawString(cell.x + PADDING,
                                  plan.height - cell.top - PADDING - ascent - index * font_size * 1.45,
                                  line.text)
        canvas.setFillColorRGB(0.25, 0.25, 0.25)
        note = " | Unicode escapes used" if any("Unicode" in warning for warning in warnings) else ""
        canvas.drawString(MARGIN, 22, f"Page {page_index} of {len(plan.pages)}{note}")
        canvas.showPage()
    canvas.save()
    data = output.getvalue()
    if len(data) > MAX_BYTES:
        raise ConversionError("The PDF exceeds 10 MiB. Select fewer rows or columns.")
    return data, {"page_count": len(plan.pages), "orientation": plan.orientation, "font_size": font_size,
                  "row_count": len(records), "column_count": len(sections[0]["headers"]),
                  "warnings": sorted(warnings), "shortened_cells": shortened, "appendix_values": appendix,
                  "checks": ["Text coverage checked", "Cell boundaries checked", "Minimum 10 pt text"]}, plan


def render_pdf_page(data, page_number=0):
    if not data.startswith(b"%PDF-") or len(data) > MAX_BYTES:
        raise ConversionError("Provide a PDF no larger than 10 MiB.")
    with PDF_LOCK:
        try:
            with pdfium.PdfDocument(data) as document:
                if not 0 <= page_number < len(document) or not 1 <= len(document) <= MAX_PAGES:
                    raise ConversionError("Choose a valid preview page (PDFs up to 200 pages).")
                page = document[page_number]
                try:
                    width, height = page.get_size()
                    if not all(math.isfinite(n) and 0 < n <= 2000 for n in (width, height)):
                        raise ConversionError("This PDF page is too large to preview.")
                    bitmap = page.render(scale=min(1000 / width, 1400 / height))
                    try:
                        with bitmap.to_pil().convert("RGB") as image:
                            output = io.BytesIO()
                            image.save(output, format="PNG")
                            return output.getvalue()
                    finally:
                        bitmap.close()
                finally:
                    page.close()
        except pdfium.PdfiumError as exc:
            raise ConversionError("This PDF could not be previewed.") from exc
