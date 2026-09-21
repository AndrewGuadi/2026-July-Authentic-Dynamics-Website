`pdf_table_reference.png` is the reviewed first-page rendering of `REFERENCE` in
`tests/test_pdf_tables.py`, exported by `build_pdf` and rasterized by PDFium through
`render_pdf_page`. The reference has three columns, two rows, a leading-zero ID,
and accented text. It checks layout/color changes with a small rasterizer tolerance.

Only replace the image after reviewing both the generated PDF and its rendered page.
Content extraction, glyph bounds, randomized layouts, and long-value coverage are
checked separately, so a new screenshot cannot approve content loss by itself.
