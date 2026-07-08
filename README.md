# Smart PDF Cropper & Label Processor

A Flask-based web application that automates shipping label processing for major Indian e-commerce platforms such as **Flipkart**, **Myntra**, and **Ajio**.

The application allows users to upload shipping-label PDFs, automatically crop platform-specific regions, extract text from selected labels, and download processed outputs.

Efficiently reduced 50% workload
---

## Features

### Flipkart

* Automatically crops the shipping label area.
* Removes unnecessary whitespace and footer sections.
* Supports multi-page PDFs.

### Myntra

* Crops barcode and shipping information based on predefined coordinates.
* Supports multi-page PDFs.

### Ajio

* Crops the required text section.
* Extracts text from the cropped region.
* Generates downloadable `.txt` files.

### Multi-Page Processing

* Processes all pages in the uploaded PDF.
* Produces a consolidated output.

### Web Interface

* Upload PDFs directly from the browser.
* Select platform from a dropdown menu.
* Download processed files instantly.

---

## Technology Stack

### Backend

* Python 3.10+
* Flask
* PyMuPDF (fitz)

### Frontend

* HTML5
* CSS3
* Jinja2 Templates

---

## Project Structure

```text
SmartPDFCropper/
│
├── app.py
│
├── templates/
│   ├── index.html
│   └── result.html
│
├── static/
│   └── style.css
│
├── uploads/
│
├── outputs/
│
├── requirements.txt
│
└── README.md
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/<your-username>/SmartPDFCropper.git
cd SmartPDFCropper
```

### Create Virtual Environment

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

or

```bash
pip install Flask PyMuPDF
```

---

## Running the Application

Start the Flask server:

```bash
python app.py
```

Output:

```text
* Running on http://127.0.0.1:5000
```

Open your browser:

```text
http://127.0.0.1:5000
```

---

## Supported Platforms

| Platform | Output                     |
| -------- | -------------------------- |
| Flipkart | Cropped PDF                |
| Myntra   | Cropped PDF                |
| Ajio     | Extracted Text File (.txt) |

---

## Workflow

### Step 1

Upload a shipping label PDF.

### Step 2

Select the platform:

* Flipkart
* Myntra
* Ajio

### Step 3

The application automatically processes the document.

#### Flipkart

```text
PDF → Crop Label → Download PDF
```

#### Myntra

```text
PDF → Crop Label → Download PDF
```

#### Ajio

```text
PDF → Crop Text Region → Extract Text → Download TXT
```

---

## Crop Coordinates

The application uses PyMuPDF coordinate rectangles:

```python
fitz.Rect(left, top, right, bottom)
```

### Flipkart

```python
fitz.Rect(191, 20, 405, 382)
```

### Myntra

```python
fitz.Rect(130, 40.5, 210, 86)
```

### Ajio

```python
left = 80
top = 225
right = rect.width - 25
bottom = rect.height - 200
crop_rect = fitz.Rect(left, top, right, bottom)
```

---

## Running on Local Network

Modify:

```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

Find your local IP address:

### Windows

```bash
ipconfig
```

Example:

```text
192.168.1.5
```

Access from another device connected to the same network:

```text
http://192.168.1.5:5000
```

---

## Deployment

### GitHub Codespaces

```bash
python app.py
```

Open the forwarded port:

```text
5000
```

### Render

1. Push project to GitHub.
2. Create a new Web Service on Render.
3. Connect repository.
4. Deploy.

### Railway

1. Connect GitHub repository.
2. Deploy application.

---

## Common Issues

### ModuleNotFoundError: No module named 'frontend'

Cause:

```bash
pip install fitz
```

Wrong package installed.

Solution:

```bash
pip uninstall fitz
pip install PyMuPDF
```

---

### TemplateNotFound

Ensure the following structure exists:

```text
templates/
├── index.html
└── result.html
```

---

### PDF Contains No Extractable Text

Some PDFs are image-based scans.

Possible solutions:

* Tesseract OCR
* EasyOCR
* Google Vision API

---

## Future Enhancements

* Drag-and-drop file uploads
* OCR support for scanned labels
* ZIP download support
* Automatic platform detection
* PDF preview before processing
* Cloud deployment
* User authentication

---
