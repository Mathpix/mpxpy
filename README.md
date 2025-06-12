# mpxpy

The official Python client for the Mathpix API. Process PDFs and images, and convert math/text content with the Mathpix API.

# Setup

## Installation

```bash
pip install mpxpy
```

## Authentication

You'll need a Mathpix API app_id and app_key to use this client. You can get these from [Mathpix Console](https://console.mathpix.com/).

Set your credentials by either:

- Using environment variables
- Passing them directly when initializing the client

MathpixClient will prioritize auth configs in the following order:

1. Passed through arguments
2. The `~/.mpx/config` file
3. ENV vars located in `.env`
4. ENV vars located in `local.env`

## Initialization

### Using environment variables

Create a config file at `~/.mpx/config` or add ENV variables to `.env` or `local.env` files:

```
MATHPIX_APP_ID=your-app-id
MATHPIX_APP_KEY=your-app-key
MATHPIX_URL=https://api.mathpix.com  # optional, defaults to this value
```

Then initialize the client:

```python
from mpxpy.mathpix_client import MathpixClient

# Will use ~/.mpx/config or environment variables
client = MathpixClient()
```

### Using arguments

You can also pass in your App ID and App Key when initializing the client:

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
    # Optional "api_url" argument sets the base URL. This can be useful for development with on-premise deployments
)
```

### Improve Mathpix

You can optionally set `improve_mathpix` to False to prevent Mathpix from retaining any outputs from a client. This can also be set on a per-request-basis, but if a client has `improve_mathpix` disabled, all requests made using that client will also be disabled.

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    improve_mathpix=False
)
```

# Process PDFs

## Basic Usage

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)

# Process a PDF file with multiple conversion formats and options
pdf = client.pdf_new(
    url="http://cs229.stanford.edu/notes2020spring/cs229-notes1.pdf",
    convert_to_docx=True,
    convert_to_md=True,
    convert_to_pptx=True,
    convert_to_md_zip=True,
    # Optional pdf-level improve_mathpix argument is default True
)

# Wait for processing to complete. Optional timeout argument is 60 seconds by default.
pdf.wait_until_complete(timeout=30)

# Get the Markdown outputs
md_output_path = pdf.to_md_file(path='output/sample.md')
md_text = pdf.to_md_text() # is type str
print(md_text)

# Get the DOCX outputs
docx_output_path = pdf.to_docx_file(path='output/sample.docx')
docx_bytes = pdf.to_docx_bytes() # is type bytes

# Get the PowerPoint outputs
pptx_output_path = pdf.to_pptx_file(path='output/sample.pptx')
pptx_bytes = pdf.to_pptx_bytes() # is type bytes

# Get the Markdown ZIP outputs (includes embedded images)
md_zip_output_path = pdf.to_md_zip_file(path='output/sample.md.zip')
md_zip_bytes = pdf.to_md_zip_bytes() # is type bytes

# Get the JSON outputs
lines_json_output_path = pdf.to_lines_json_file(path='output/sample.lines.json')
lines_json = pdf.to_lines_json() # parses JSON into type Dict
```

## Pdf Class Documentation

### Properties

- `auth`: An Auth instance with Mathpix credentials.
- `pdf_id`: The unique identifier for this PDF.
- `file_path`: Path to a local PDF file.
- `url`: URL of a remote PDF file.
- `convert_to_docx`: Optional boolean to automatically convert your result to docx
- `convert_to_md`: Optional boolean to automatically convert your result to md
- `convert_to_mmd`: Optional boolean to automatically convert your result to mmd
- `convert_to_tex_zip`: Optional boolean to automatically convert your result to tex.zip
- `convert_to_html`: Optional boolean to automatically convert your result to html
- `convert_to_pdf`: Optional boolean to automatically convert your result to pdf
- `convert_to_md_zip`: Optional boolean to automatically convert your result to md.zip (markdown with embedded images)
- `convert_to_mmd_zip`: Optional boolean to automatically convert your result to mmd.zip (Mathpix markdown with embedded images)
- `convert_to_pptx`: Optional boolean to automatically convert your result to pptx (PowerPoint)

### Methods

- `wait_until_complete`: Wait for the PDF processing and optional conversions to complete.
- `pdf_status`: Get the current status of the PDF processing.
- `pdf_conversion_status`: Get the current status of the PDF conversions.
- `to_docx_file`: Save the processed PDF result to a DOCX file at a local path.
- `to_docx_bytes`: Get the processed PDF result as DOCX bytes.
- `to_md_file`: Save the processed PDF result to a Markdown file at a local path.
- `to_md_text`: Get the processed PDF result as a Markdown string.
- `to_mmd_file`: Save the processed PDF result to a Mathpix Markdown file at a local path.
- `to_mmd_text`: Get the processed PDF result as a Mathpix Markdown string.
- `to_tex_zip_file`: Save the processed PDF result to a tex.zip file at a local path.
- `to_tex_zip_bytes`: Get the processed PDF result in tex.zip format as bytes.
- `to_html_file`: Save the processed PDF result to a HTML file at a local path.
- `to_html_bytes`: Get the processed PDF result in HTML format as bytes.
- `to_pdf_file`: Save the processed PDF result to a PDF file at a local path.
- `to_pdf_bytes`: Get the processed PDF result in PDF format as bytes.
- `to_lines_json_file`: Save the processed PDF line-by-line result to a JSON file at a local path.
- `to_lines_json`: Get the processed PDF result in JSON format.
- `to_lines_mmd_json_file`: Save the processed PDF line-by-line result, including Mathpix Markdown, to a JSON file at a local path.
- `to_lines_mmd_json`: Get the processed PDF result in JSON format with text in Mathpix Markdown.
- `to_md_zip_file`: Save the processed PDF result to a ZIP file containing markdown output and any embedded images.
- `to_md_zip_bytes`: Get the processed PDF result in ZIPPED markdown format as bytes.
- `to_mmd_zip_file`: Save the processed PDF result to a ZIP file containing Mathpix Markdown output and any embedded images.
- `to_mmd_zip_bytes`: Get the processed PDF result in ZIPPED Mathpix Markdown format as bytes.
- `to_pptx_file`: Save the processed PDF result to a PPTX file.
- `to_pptx_bytes`: Get the processed PDF result in PPTX format as bytes.

# Process Images

## Basic Usage

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)
# Process an image file
image = client.image_new(
    url="https://mathpix-ocr-examples.s3.amazonaws.com/cases_hw.jpg"
    # Optional image-level improve_mathpix argument is default True
)

# Get the Mathpix Markdown (MMD) representation
mmd = image.mmd()
print(mmd)

# Get line-by-line OCR data
lines = image.lines_json()
print(lines)
```

## Image Class Documentation

### Properties

- `auth`: An Auth instance with Mathpix credentials.
- `file_path`: Path to a local image file, if using a local file.
- `url`: URL of a remote image, if using a remote file.

### Methods

- `lines_json`: Get line-by-line OCR data for the image.
- `mmd`: Get the Mathpix Markdown (MMD) representation of the image.

# Convert Mathpix Markdown (MMD)

## Basic Usage

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)

# Similar to Pdf, Conversion class takes separate arguments for each conversion format
conversion = client.conversion_new(
    mmd="\\frac{1}{2} + \\sqrt{3}",
    convert_to_docx=True,
    convert_to_md=True,
    convert_to_mmd_zip=True,
    convert_to_pptx=True,
)

# Wait for conversion to complete
conversion.wait_until_complete(timeout=30)

# Get the Markdown outputs
md_output_path = conversion.to_md_file(path='output/sample.md')
md_text = conversion.to_md_text() # is of type str

# Get the DOCX outputs
docx_output_path = conversion.to_docx_file(path='output/sample.docx')
docx_bytes = conversion.to_docx_bytes() # is of type bytes

# Get the Mathpix Markdown ZIP outputs (includes embedded images)
mmd_zip_output_path = conversion.to_mmd_zip_file(path='output/sample.mmd.zip')
mmd_zip_bytes = conversion.to_mmd_zip_bytes() # is of type bytes

# Get the PowerPoint outputs
pptx_output_path = conversion.to_pptx_file(path='output/sample.pptx')
pptx_bytes = conversion.to_pptx_bytes() # is of type bytes
```

## Conversion Class Documentation

### Properties

- `auth`: An Auth instance with Mathpix credentials.
- `conversion_id`: The unique identifier for this conversion.
- `convert_to_docx`: Optional boolean to automatically convert your result to docx
- `convert_to_md`: Optional boolean to automatically convert your result to md
- `convert_to_tex_zip`: Optional boolean to automatically convert your result to tex.zip
- `convert_to_html`: Optional boolean to automatically convert your result to html
- `convert_to_pdf`: Optional boolean to automatically convert your result to pdf
- `convert_to_latex_pdf`: Optional boolean to automatically convert your result to pdf containing LaTeX
- `convert_to_md_zip`: Optional boolean to automatically convert your result to md.zip (markdown with embedded images)
- `convert_to_mmd_zip`: Optional boolean to automatically convert your result to mmd.zip (Mathpix markdown with embedded images)
- `convert_to_pptx`: Optional boolean to automatically convert your result to pptx (PowerPoint)

### Methods

- `wait_until_complete`: Wait for the conversion to complete.
- `conversion_status`: Get the current status of the conversion.
- `to_docx_file`: Save the processed conversion result to a DOCX file at a local path.
- `to_docx_bytes`: Get the processed conversion result as DOCX bytes.
- `to_md_file`: Save the processed conversion result to a Markdown file at a local path.
- `to_md_text`: Get the processed conversion result as a Markdown string.
- `to_mmd_file`: Save the processed conversion result to a Mathpix Markdown file at a local path.
- `to_mmd_text`: Get the processed conversion result as a Mathpix Markdown string.
- `to_tex_zip_file`: Save the processed conversion result to a tex.zip file at a local path.
- `to_tex_zip_bytes`: Get the processed conversion result in tex.zip format as bytes.
- `to_html_file`: Save the processed conversion result to a HTML file at a local path.
- `to_html_bytes`: Get the processed conversion result in HTML format as bytes.
- `to_pdf_file`: Save the processed conversion result to a PDF file at a local path.
- `to_pdf_bytes`: Get the processed conversion result in PDF format as bytes.
- `to_latex_pdf_file`: Save the processed conversion result to a PDF file containing LaTeX at a local path.
- `to_latex_pdf_bytes`: Get the processed conversion result in PDF format as bytes (with LaTeX).
- `to_md_zip_file`: Save the processed conversion result to a ZIP file containing markdown output and any embedded images.
- `to_md_zip_bytes`: Get the processed conversion result in ZIPPED markdown format as bytes.
- `to_mmd_zip_file`: Save the processed conversion result to a ZIP file containing Mathpix Markdown output and any embedded images.
- `to_mmd_zip_bytes`: Get the processed conversion result in ZIPPED Mathpix Markdown format as bytes.
- `to_pptx_file`: Save the processed conversion result to a PPTX file.
- `to_pptx_bytes`: Get the processed conversion result in PPTX format as bytes.

# Error Handling

The client provides detailed error information in the following classes:

- MathpixClientError
- AuthenticationError
- ValidationError
- FilesystemError
- ConversionIncompleteError

```python
from mpxpy.mathpix_client import MathpixClient
from mpxpy.errors import MathpixClientError, ConversionIncompleteError

client = MathpixClient(app_id="your-app-id", app_key="your-app-key")

try:
    pdf = client.pdf_new(file_path="example.pdf", convert_to_docx=True)
except FileNotFoundError as e:
    print(f"File not found: {e}")
except MathpixClientError as e:
    print(f"File upload error: {e}")
try:
    pdf.to_docx_file('output/path/example.pdf')
except ConversionIncompleteError as e:
    print(f'Conversions are not complete')
```

# Development

## Setup

```bash
# Clone the repository
git clone git@github.com:Mathpix/mpxpy.git
cd mpxpy

# Install in development mode
pip install -e .
# Or install using the requirements.txt file
pip install -r requirements.txt
```

## Running Tests

To run tests you will need to add [authentication](#authentication).

```bash
# Install test dependencies
pip install -e ".[dev]"
# Or install using the requirements.txt file
pip install -r requirements.txt
# Run tests
pytest
```
