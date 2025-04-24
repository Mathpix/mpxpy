# mpxpy

The official Python client for the Mathpix API. Process PDFs, images, and convert math/text content with the Mathpix API.

## Installation

```bash
pip install mpxpy
```

## Authentication

You'll need a Mathpix API app_id and app_key to use this client. You can get these from the [Mathpix Console](https://console.mathpix.com/).

Set your credentials by either:
- Using environment variables
- Passing them directly when initializing the client

MathpixClient will prioritize auth configs in the following order:
1. Passed through arguments
2. The `~/.mpx/config` file
3. ENV vars located in `.env`
4. ENV vars located in `local.env`

### Using environment variables

Create a config file at `~/.mpx/config` or add ENV variables to `.env` or `local.env` files:

```
MATHPIX_APP_ID=your-app-id
MATHPIX_APP_KEY=your-app-key
MATHPIX_URL=https://api.mathpix.com  # optional, defaults to this value
```

### Passing credentials directly

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)
```

Then initialize the client:

```python
from mpxpy.mathpix_client import MathpixClient

# Will use ~/.mpx/config or environment variables
client = MathpixClient()

# Will use passed arguments
client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)
```

## Features

### Process a PDF

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)

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

### Process an Image

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)
# Process an image file
image = client.image_new(
    file_url="https://mathpix-ocr-examples.s3.amazonaws.com/cases_hw.jpg"
)

# Get the Mathpix Markdown (MMD) representation
mmd = image.mmd()
print(mmd)

# Get line-by-line OCR data
lines = image.lines_json()
print(lines)
```

### Convert Mathpix Markdown (MMD)

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)
# Convert Mathpix Markdown to various formats
conversion = client.conversion_new(
    mmd="\\frac{1}{2}",
    conversion_formats={"docx": True}
)

# Wait for conversion to complete
conversion.wait_until_complete(timeout=30)

# Download the converted output
docx_output = conversion.download_output("docx")
```

## Error Handling

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
    pdf = client.pdf_new(file_path="example.pdf", conversion_formats={'docx': True})
except FileNotFoundError as e:
    print(f"File not found: {e}")
except MathpixClientError as e:
    print(f"File upload error: {e}")
try:
    pdf.download_output_to_local_path('docx', 'output/path')
except ConversionIncompleteError as e:
    print(f'Conversions are not complete')
```

## Development

### Setup

```bash
# Clone the repository
git clone git@github.com:Mathpix/mpxpy.git
cd mpxpy

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