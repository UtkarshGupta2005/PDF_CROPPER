from flask import Flask, render_template, request, send_file, redirect, url_for
import fitz  # PyMuPDF
import os

app = Flask(__name__)

# Ensure folders exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)


@app.route('/')
def index():
    """Landing page for upload"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles PDF upload and cropping"""
    platform = request.form.get('platform')
    file = request.files.get('file')
    
    if not file:
        return "No file uploaded", 400

    # Save uploaded file
    input_path = os.path.join("uploads", file.filename)
    file.save(input_path)

    # Open the uploaded PDF
    doc = fitz.open(input_path)
    new_doc = fitz.open()

    # Loop through all pages and crop based on platform
    for page_number in range(len(doc)):
        page = doc[page_number]
        rect = page.rect  # Original page dimensions

        # 🔹 Define crop coordinates based on platform
        if platform == 'flipkart':
            # Removes whitespace & keeps only main label
            crop_rect = fitz.Rect(0, 20, 400, 380)

        elif platform == 'myntra':
            # Slightly wider layout
            crop_rect = fitz.Rect(80, 40, 209, 85)

        elif platform == 'ajio':
            # Clean crop preserving "Shipment#" barcode text
            left = 30
            top = 112
            right = rect.width - 25
            bottom = rect.height - 200
            crop_rect = fitz.Rect(left, top, right, bottom)

        else:
            # Default - full page (no crop)
            crop_rect = rect

        # 🔹 Crop the page
        page.set_cropbox(crop_rect)

        # Add cropped page to new PDF
        new_page = new_doc.new_page(width=crop_rect.width, height=crop_rect.height)
        new_page.show_pdf_page(fitz.Rect(0, 0, crop_rect.width, crop_rect.height), doc, page_number, clip=crop_rect)

    # Save cropped multi-page PDF
    output_filename = f"cropped_{platform}_{file.filename}"
    output_path = os.path.join("outputs", output_filename)
    new_doc.save(output_path)
    new_doc.close()
    doc.close()

    # Redirect user to result page
    return redirect(url_for('result', filename=output_filename))


@app.route('/result/<filename>')
def result(filename):
    """Displays result page after cropping"""
    return render_template('result.html', filename=filename)


@app.route('/download/<filename>')
def download_file(filename):
    """Serves the cropped file for download"""
    path = os.path.join("outputs", filename)
    if not os.path.exists(path):
        return "File not found.", 404
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    # Run on local network for multi-device access
    app.run(host='0.0.0.0', port=5000, debug=True)
