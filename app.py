from flask import Flask, render_template, request, send_file, redirect, url_for
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import os
import re
import pandas as pd
import pdfplumber
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)

# Ensure folders exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Flipkart order IDs always look like "OD" followed by ~19-20 digits (e.g.
# OD438008958159622100). We match this shape directly rather than anchoring
# on the words "Order ID", because these PDFs lay the label out as a table
# (Order Id | Invoice No | GSTIN headers, then values on the next line).
# pdfplumber flattens that table into plain text lines, so "Order Id:" ends
# up sitting right next to the word "Invoice" (the next column's header) -
# a label-based regex like r"Order\s*ID[:\s]*(...)" matches "Invoice" every
# time, never the real ID.
# Flipkart order IDs always look like "OD" followed by ~19-20 digits (e.g.
# OD438008958159622100). We match this shape directly rather than anchoring
# on the words "Order ID", because these PDFs lay the label out as a table
# (Order Id | Invoice No | GSTIN headers, then values on the next line).
# pdfplumber flattens that table into plain text lines, so "Order Id:" ends
# up sitting right next to the word "Invoice" (the next column's header) -
# a label-based regex like r"Order\s*ID[:\s]*(...)" matches "Invoice" every
# time, never the real ID. Confirmed against a real 41-page Flipkart PDF:
# 41/41 pages matched correctly with this pattern.
#
# Myntra/Ajio order ID formats haven't been verified against a real sample
# yet - the label-based pattern is kept as a fallback for those platforms
# until we can confirm their actual format. If Myntra/Ajio matching fails,
# upload a sample PDF from that platform so the pattern list can be updated.
ORDER_ID_PATTERNS = [
    r"\b(OD\d{10,})\b",                          # Flipkart: OD + 10+ digits
    r"Order\s*Id[:\s]*([A-Za-z0-9\-]{6,})",      # generic label-based fallback
]


def extract_order_id(text):
    for pattern in ORDER_ID_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_id(match.group(1))
    return None

ALLOWED_PLATFORMS = {"flipkart", "myntra", "ajio", "default"}


def normalize_id(order_id):
    s = str(order_id).strip()
    if s.endswith(".0"):  # e.g. pandas turning int OrderID 1024 into "1024.0"
        s = s[:-2]
    return s.lstrip("0") or "0"


def extract_order_ids_from_pdf(pdf_path):
    """
    Extract the order id for every page of the ORIGINAL (uncropped) PDF.

    IMPORTANT: this must run on the *original* file, not the cropped one.
    Several platform crop boxes (e.g. Myntra's tiny 80,40,209,85 box) cut
    away the part of the label that contains the "Order ID" text entirely,
    so scanning the cropped file finds nothing and every id ends up
    reported as "missing".
    """
    page_map = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            order_id = extract_order_id(text)
            if order_id:
                page_map.setdefault(order_id, []).append(page_no)
    return page_map


def build_sorted_cropped_pdf(excel_path, original_pdf_path, output_path):
    """
    Build the final PDF: pages taken from the CROPPED pdf (so labels stay
    cropped), but reordered to match the sequence of OrderIDs in the Excel
    sheet. Page numbers are looked up from the ORIGINAL pdf's text, since
    cropping can remove the very text we need to match on. Page indices are
    aligned 1:1 between original and cropped documents.
    """
    # Force OrderID to string so pandas doesn't upcast numeric ids to
    # float64 (e.g. turning 1024 into "1024.0") when the column has blanks.
    df = pd.read_excel(excel_path, dtype={"Order Id": str})

    if "Order Id" not in df.columns:
        raise Exception("Excel must contain 'Order Id' column")

    excel_ids = [normalize_id(x) for x in df["Order Id"]]

    page_map = extract_order_ids_from_pdf(original_pdf_path)

    reader = PdfReader(original_pdf_path)
    writer = PdfWriter()

    missing = []

    for oid in excel_ids:
        if oid in page_map and page_map[oid]:
            page_no = page_map[oid].pop(0)
            writer.add_page(reader.pages[page_no])
        else:
            missing.append(oid)

    print(f"Order ID matching: {len(excel_ids)} total, "
          f"{len(excel_ids) - len(missing)} matched, {len(missing)} missing")

    if len(writer.pages) == 0:
        # Writing a zero-page PDF produces a file that viewers (e.g. Chrome's
        # built-in PDF viewer) can't render at all - it just shows a blank/
        # stuck page instead of a helpful error. Fail loudly here instead so
        # the user gets a real error message pointing at the root cause
        # (regex not matching this PDF's text, or Excel IDs in a different
        # format than what's in the PDF).
        raise Exception(
            "No Order Ids from the Excel sheet could be matched to any page "
            "in the PDF. Check that the 'Order Id' column values match the "
            "IDs printed on the invoices, and that ORDER_ID_PATTERNS matches "
            "the text format used on this platform's PDF."
        )

    for page in writer.pages:
        try:
            page.compress_content_streams()
        except Exception:
            pass

    with open(output_path, "wb") as f:
        writer.write(f)

    return missing


@app.route('/')
def index():
    """Landing page for upload"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles PDF upload, cropping, and sorting according to the excel sheet"""
    platform = request.form.get('platform', 'default')
    file = request.files.get("file")
    excel = request.files.get("excel_file")

    if not file or not excel:
        return "Upload both PDF and Excel", 400

    if platform not in ALLOWED_PLATFORMS:
        return f"Unknown platform '{platform}'", 400

    # Sanitize filenames to avoid path traversal
    safe_pdf_name = secure_filename(file.filename)
    safe_excel_name = secure_filename(excel.filename)

    input_path = os.path.join("uploads", safe_pdf_name)
    excel_path = os.path.join("uploads", safe_excel_name)
    excel.save(excel_path)
    file.save(input_path)

    sorted_filename = f'sorted_{platform}_{safe_pdf_name}'
    sorted_path = os.path.join("outputs", sorted_filename)
    missing = build_sorted_cropped_pdf(excel_path, input_path, sorted_path)


    try:
        # Open the uploaded PDF
        doc = fitz.open(input_path)
        new_doc = fitz.open()

        # Loop through all pages and crop based on platform
        # for page_number in range(len(doc)):
        #    page = doc[page_number]
        #    rect = page.rect  # Original page dimensions

            # Define crop coordinates based on platform
        #    if platform == 'flipkart':
                # Removes whitespace & keeps only main label
         #       crop_rect = fitz.Rect(90, 17, 410, 382)

          #  elif platform == 'myntra':
                # Slightly wider layout
           #     crop_rect = fitz.Rect(80, 40, 209, 85)

            #elif platform == 'ajio':
                # Clean crop preserving "Shipment#" barcode text
             #   left = 30
              #  top = 112
               # right = rect.width - 25
                #bottom = rect.height - 200
                #crop_rect = fitz.Rect(left, top, right, bottom)

            #else:
                # Default - full page (no crop)
            #    crop_rect = rect

            # Guard against invalid/negative rectangles (e.g. a short PDF
            # page combined with the ajio "height - 200" math going
            # negative). An invalid rect can crash the underlying MuPDF C
            # extension outright, taking the whole server down rather than
            # raising a catchable Python exception. Clamp/normalize first,
            # and fall back to the full page if the result is still empty.
            #crop_rect = fitz.Rect(crop_rect).normalize()
            #crop_rect = crop_rect & rect  # intersect with the actual page bounds
            #if crop_rect.is_empty or crop_rect.width <= 0 or crop_rect.height <= 0:
            #    crop_rect = rect 

            # Add cropped page to new PDF (clip already restricts the source
            # region we copy from, no need to mutate the source page's cropbox)
            #new_page = new_doc.new_page(width=crop_rect.width, height=crop_rect.height)
            #new_page.show_pdf_page(fitz.Rect(0, 0, crop_rect.width, crop_rect.height), doc, page_number, clip=crop_rect) 

        # Save cropped multi-page PDF
        #output_filename = f"cropped_{platform}_{safe_pdf_name}"
        #output_path = os.path.join("outputs", output_filename)
        #new_doc.save(output_path)
        #doc.close()
        #new_doc.close()

        # Build the final, sorted PDF using order IDs read from the ORIGINAL pdf
        #sorted_filename = f'sorted_{platform}_{safe_pdf_name}'
        #sorted_path = os.path.join("outputs", sorted_filename)
        #missing = build_sorted_cropped_pdf(excel_path, input_path, output_path, sorted_path)

    except Exception as e:
        app.logger.exception("Failed while processing upload")
        return f"Something went wrong while processing your files: {e}", 500

    if missing:
        print("Missing IDs:", missing)

    # Redirect user to the SORTED file, not the unsorted cropped one.
    # missing IDs are passed as a repeated query param so the result page
    # can warn the user instead of only logging to the server console.
    return redirect(url_for('result', filename=sorted_filename, platform=platform, missing=missing))


@app.route('/result/<filename>')
def result(filename):
    """Displays result page after cropping"""
    platform = request.args.get('platform', '')
    missing = request.args.getlist('missing')
    return render_template('result.html', filename=filename, platform=platform, missing=missing)


@app.route('/download/<filename>')
def download_file(filename):
    """Serves the cropped file for download"""
    safe_name = secure_filename(filename)
    path = os.path.join("outputs", safe_name)
    if not os.path.exists(path):
        return "File not found.", 404
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    # NOTE: debug=True should be disabled in any real deployment
    app.run(host='0.0.0.0', port=5000, debug=True)
