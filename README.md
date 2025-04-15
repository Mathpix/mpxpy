# Mathpix Python Client

The official Python client for the Mathpix API. Process PDFs, images, and convert math/text content with the Mathpix API.

## Installation

```bash
pip install mathpix
```

## Authentication

You'll need a Mathpix API app_id and app_key to use this client. You can get these from the [Mathpix Console](https://console.mathpix.com/).

Set your credentials using either environment variables or pass them directly when initializing the client. MathpixClient will prioritize auth configs passed through arguments over ENV vars

### Using environment variables

Create a `local.env` file:

```
MATHPIX_APP_ID=your-app-id
MATHPIX_APP_KEY=your-app-key
MATHPIX_URL=https://api.mathpix.com  # optional, defaults to this value
```

### Passing credentials directly

```python
from mathpix.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)
```

Then initialize the client:

```python
from mathpix.mathpix_client import MathpixClient

client = MathpixClient()  # Will use environment variables
```

## Features

### Process a PDF

```python
from mathpix.mathpix_client import MathpixClient
client = MathpixClient()

# Process a PDF file
pdf_file = client.pdf_new(
    file_url="http://cs229.stanford.edu/notes2020spring/cs229-notes1.pdf",
    conversion_formats={
        "docx": True,
        "md": True
    }
)

# Wait for processing to complete
pdf_file.wait_until_complete(timeout=60)

# Download the converted files
pdf_file.download_output_to_local_path("docx", "./output")
pdf_file.download_output_to_local_path("md", "./output")
```

### Process an Image with Math Content

```python
from mathpix.mathpix_client import MathpixClient
client = MathpixClient()

# Process an image file
image = client.image_new(
    file_url="https://mathpix-ocr-examples.s3.amazonaws.com/cases_hw.jpg"
)

# Get the Mathpix Markdown (MMD) representation
mmd = image.mmd()
print(mmd)

# Get line-by-line OCR data
lines = image.lines_json()
```

### Convert Mathpix Markdown (MMD)

```python
from mathpix.mathpix_client import MathpixClient
client = MathpixClient()

# Convert Mathpix Markdown to various formats
conversion = client.conversion_new(
    mmd="\\frac{1}{2}",
    formats={"latex": {}}
)

# Wait for conversion to complete
conversion.wait_until_complete(timeout=30)

# Download the converted output
latex_output = conversion.download_output("latex")
```

## Error Handling

The client provides detailed error information:

```python
from mathpix.mathpix_client import MathpixClient, MathpixClientError

client = MathpixClient(app_id="your-app-id", app_key="your-app-key")

try:
    pdf_file = client.pdf_new(file_path="nonexistent.pdf")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except MathpixClientError as e:
    print(f"API error: {e}")
```

## Development

### Setup

```bash
# Clone the repository
git clone git@github.com:Mathpix/mathpix-python.git
cd mathpix-python

# Install in development mode
pip install -e .
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest
```