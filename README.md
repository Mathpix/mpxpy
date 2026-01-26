# mpxpy

The official Python client for the Mathpix API. Process PDFs and images, and convert math/text content with the Mathpix API.

## Setup

### Installation

```bash
pip install mpxpy
```

### Authentication

You'll need a Mathpix API app_id and app_key to use this client. You can get these from [Mathpix Console](https://console.mathpix.com/).

Set your credentials by either:

- Using environment variables
- Passing them directly when initializing the client

MathpixClient will prioritize auth configs in the following order:

1. Passed through arguments
2. The `~/.mpx/config` file
3. ENV vars located in `.env`
4. ENV vars located in `local.env`

### Initialization

#### Using environment variables

Create a config file at `~/.mpx/config` or add ENV variables to `.env` or `local.env` files:

```bash
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

#### Using arguments

You can also pass in your App ID and App Key when initializing the client:

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
    # Optional "api_url" argument sets the base URL. This can be useful for development with on-premise deployments
)
```

#### Improve Mathpix

You can optionally set `improve_mathpix` to False to prevent Mathpix from retaining any outputs from a client. This can also be set on a per-request-basis, but if a client has `improve_mathpix` disabled, all requests made using that client will also be disabled.

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    improve_mathpix=False
)
```

## Process PDFs

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)

# Process a PDF file with multiple conversion formats and options
pdf = client.pdf_new(
    file_path='/path/to/pdf/sample.pdf',
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

## Process Images

```python
from mpxpy.mathpix_client import MathpixClient

client = MathpixClient(
    app_id="your-app-id",
    app_key="your-app-key"
)
# Process an image file
image = client.image_new(
    file_path='/path/to/image/sample.jpg',
    # Optional image-level improve_mathpix argument is default True
)

# Process an image file with various options
tagged_image = client.image_new(
    file_path='/path/to/image/sample.jpg',
    tags=['tag']
)
include_line_data = client.image_new(
    file_path='/path/to/image/sample.jpg',
    include_line_data=True
)

# Get the full response
result = image.results()
print(result)

# Get the Mathpix Markdown (MMD) representation
mmd = image.mmd()
print(mmd)

# Get line-by-line OCR data
lines = image.lines_json()
print(lines)

# Make an async image request and get its results
async_image = client.image_new(
    file_path='/path/to/image/sample.jpg',
    is_async=True
)
async_image.wait_until_complete(timeout=5)
result = async_image.results()
```

## Convert Mathpix Markdown (MMD)

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

## API Reference

### `MathpixClient`

The MathpixClient class is used to add authenticate and create requests.

#### `MathpixClient` Constructor

##### `MathpixClient` Constructor Arguments

- `app_id`: Optional Mathpix application ID. If None, will use environment variable.
- `app_key`: Optional Mathpix application key. If None, will use environment variable.
- `api_url`: Optional Mathpix API URL. If None, will use environment variable or default to the production API.
- `improve_mathpix`: Optional boolean to enable Mathpix to retain user output. Default is true.
- `request_options`: Optional dict of keyword arguments to pass to the requests. Default is None.

#### `MathpixClient` Properties

- `auth`: An Auth instance managing API credentials and endpoints.
- `improve_mathpix`: Boolean to enable/disable Mathpix retaining user output.
- `request_options`: Dict of keyword arguments passed to the requests library. Default is None.

#### `MathpixClient` Methods

##### `MathpixClient.image_new`

Returns a new Image instance

###### `MathpixClient.image_new` Arguments

- `file_path`: Path to a local image file.
- `url`: URL of a remote image.
- `improve_mathpix`: Optional boolean to enable Mathpix to retain user output.
- `metadata`: Optional dict to attach metadata to a request
- `tags`: Optional list of strings which can be used to identify results using the /v3/ocr-results endpoint
- `is_async`: Optional boolean to enable non-interactive requests
- `callback`: Optional Callback Object (see [Callback Object](https://docs.mathpix.com/#callback-object))
- `formats`: Optional list of formats ('text', 'data', 'html', or 'latex_styled')
- `data_options`: Optional DataOptions dict (see [DataOptions Object](https://docs.mathpix.com/#dataoptions-object))
- `include_detected_alphabets`: Optional boolean to return the detected alphabets
- `alphabets_allowed`: Optional dict to list alphabets allowed in the output (see [AlphabetsAllowed Object](https://docs.mathpix.com/#alphabetsallowed-object))
- `region`: Optional dict to specify the image area with pixel coordinates 'top_left_x', 'top_left_y', 'width', 'height'
- `enable_blue_hsv_filter`: Optional boolean to enable a special mode of image processing where it processes blue hue text exclusively
- `confidence_threshold`: Optional number between 0 and 1 to specify a threshold for triggering confidence errors (file level threshold)
- `confidence_rate_threshold`: Optional number between 0 and 1 to specify a threshold for triggering confidence errors, default 0.75 (symbol level threshold)
- `include_equation_tags`: Optional boolean to specify whether to include equation number tags inside equations LaTeX. When set to True, it sets "idiomatic_eqn_arrays": True because equation numbering works better in those environments compared to the array environment
- `include_line_data`: Optional boolean to return information segmented line by line
- `include_word_data`: Optional boolean to return information segmented word by word
- `include_smiles`: Optional boolean to enable experimental chemistry diagram OCR via RDKIT normalized SMILES
- `include_inchi`: Optional boolean to include InChI data as XML attributes inside `<smiles>` elements
- `include_geometry_data`: Optional boolean to enable data extraction for geometry diagrams (currently only supports triangle diagrams)
- `include_diagram_text`: Optional boolean to enable text extraction from diagrams (for use with "include_line_data": True). The extracted text will be part of line data, and not part of the "text" or any other output format specified. the "parent_id" of these text lines will correspond to the "id" of one of the diagrams in the line data. Diagrams will also have "children_ids" to store references to those text lines
- `auto_rotate_confidence_threshold`: Optional number between 0 and 1 to specify threshold for auto rotating images to the correct orientation, default 0.99
- `rm_spaces`: Optional boolean to determine whether extra white space is removed from equations in "latex_styled" and "text" formats
- `rm_fonts`: Optional boolean to determine whether font commands such as \mathbf and \mathrm are removed from equations in "latex_styled" and "text" formats
- `idiomatic_eqn_arrays`: Optional boolean to specify whether to use aligned, gathered, or cases instead of an array environment for a list of equations
- `idiomatic_braces`: Optional boolean to specify whether to remove unnecessary braces for LaTeX output
- `numbers_default_to_math`: Optional boolean to specify whether numbers are always math
- `math_fonts_default_to_math`: Optional boolean to specify whether math fonts are always math
- `math_inline_delimiters`: Optional [str, str] tuple to specify begin inline math and end inline math delimiters for "text" outputs
- `math_display_delimiters`: Optional [str, str] tuple to specify begin display math and end display math delimiters for "text" outputs
- `enable_spell_check`: Optional boolean to enable a predictive mode for English handwriting
- `enable_tables_fallback`: Optional boolean to enable an advanced table processing algorithm that supports very large and complex tables
- `fullwidth_punctuation`: Optional boolean to specify whether punctuation will be fullwidth Unicode

##### `MathpixClient.pdf_new`

Returns a new Pdf instance.

###### `MathpixClient.pdf_new` Arguments

- `file_path`: Path to a local PDF file.
- `url`: URL of a remote PDF file.
- `metadata`: Optional dict to attach metadata to a request
- `alphabets_allowed`: Optional dict to list alphabets allowed in the output (see [AlphabetsAllowed Object](https://docs.mathpix.com/#alphabetsallowed-object))
- `rm_spaces`: Optional boolean to determine whether extra white space is removed from equations in "latex_styled" and "text" formats
- `rm_fonts`: Optional boolean to determine whether font commands such as \mathbf and \mathrm are removed from equations in "latex_styled" and "text" formats
- `idiomatic_eqn_arrays`: Optional boolean to specify whether to use aligned, gathered, or cases instead of an array environment for a list of equations
- `include_equation_tags`: Optional boolean to specify whether to include equation number tags inside equations LaTeX. When set to True, it sets "idiomatic_eqn_arrays": True because equation numbering works better in those environments compared to the array environment
- `include_smiles`: Optional boolean to enable experimental chemistry diagram OCR via RDKIT normalized SMILES
- `include_chemistry_as_image`: Optional boolean to return an image crop containing SMILES in the alt-text for chemical diagrams
- `include_diagram_text`: Optional boolean to enable text extraction from diagrams (for use with "include_line_data": True). The extracted text will be part of line data, and not part of the "text" or any other output format specified. the "parent_id" of these text lines will correspond to the "id" of one of the diagrams in the line data. Diagrams will also have "children_ids" to store references to those text lines
- `numbers_default_to_math`: Optional boolean to specify whether numbers are always math
- `math_inline_delimiters`: Optional [str, str] tuple to specify begin inline math and end inline math delimiters for "text" outputs
- `math_display_delimiters`: Optional [str, str] tuple to specify begin display math and end display math delimiters for "text" outputs
- `page_ranges`: Specifies a page range as a comma-separated string. Examples include 2,4-6 which selects pages [2,4,5,6] and 2 - -2 which selects all pages starting with the second page and ending with the next-to-last page
- `enable_spell_check`: Optional boolean to enable a predictive mode for English handwriting
- `auto_number_sections`: Optional[bool] = False,
- `remove_section_numbering`: Specifies whether to remove existing numbering for sections and subsections. Defaults to false
- `preserve_section_numbering`: Specifies whether to keep existing section numbering as is. Defaults to true
- `enable_tables_fallback`: Optional boolean to enable an advanced table processing algorithm that supports very large and complex tables
- `fullwidth_punctuation`: Optional boolean to specify whether punctuation will be fullwidth Unicode
- `convert_to_docx`: Optional boolean to automatically convert your result to docx
- `convert_to_md`: Optional boolean to automatically convert your result to md
- `convert_to_mmd`: Optional boolean to automatically convert your result to mmd
- `convert_to_tex_zip`: Optional boolean to automatically convert your result to tex.zip
- `convert_to_html`: Optional boolean to automatically convert your result to html
- `convert_to_pdf`: Optional boolean to automatically convert your result to pdf
- `convert_to_md_zip`: Optional boolean to automatically convert your result to md.zip
- `convert_to_mmd_zip`: Optional boolean to automatically convert your result to mmd.zip
- `convert_to_pptx`: Optional boolean to automatically convert your result to pptx
- `convert_to_html_zip`: Optional boolean to automatically convert your result to html.zip
- `improve_mathpix`: Optional boolean to enable Mathpix to retain user output. Default is true
- `file_batch_id`: Optional batch ID to associate this file with.

##### `MathpixClient.conversion_new`

Returns a new Conversion instance.

###### `MathpixClient.conversion_new` Arguments

- `mmd`: Mathpix Markdown content to convert.
- `convert_to_docx`: Optional boolean to convert your result to docx
- `convert_to_md`: Optional boolean to convert your result to md
- `convert_to_tex_zip`: Optional boolean to convert your result to tex.zip
- `convert_to_html`: Optional boolean to convert your result to html
- `convert_to_pdf`: Optional boolean to convert your result to pdf
- `convert_to_latex_pdf`: Optional boolean to convert your result to pdf containing LaTeX
- `convert_to_md_zip`: Optional boolean to automatically convert your result to md.zip
- `convert_to_mmd_zip`: Optional boolean to automatically convert your result to mmd.zip
- `convert_to_pptx`: Optional boolean to automatically convert your result to pptx
- `convert_to_html_zip`: Optional boolean to automatically convert your result to html.zip

##### `MathpixClient.batch_new`

Submits multiple images for batch processing. Returns a Batch instance.

###### `MathpixClient.batch_new` Arguments

- `urls`: Dict mapping keys to image sources. Values can be string URLs, data URLs, or objects with per-item options.
- `ocr_behavior`: Processing mode - "latex" (default) or "text".
- `callback`: Optional callback configuration for async notification.
- `metadata`: Optional metadata dict to attach to the request.
- `formats`: Optional list of output formats (applies to all items unless overridden).
- `data_options`: Optional DataOptions dict for text mode.
- `include_detected_alphabets`: Return detected alphabets in results.
- `alphabets_allowed`: Dict specifying allowed alphabets.
- `confidence_threshold`: File-level confidence threshold (0-1).
- `confidence_rate_threshold`: Symbol-level confidence threshold (0-1).

##### `MathpixClient.strokes_new`

Recognizes handwritten strokes. Returns the API response dict with latex, text, and confidence.

###### `MathpixClient.strokes_new` Arguments

- `strokes`: Dict with 'x' and 'y' keys, each containing list of strokes. Example: `{"x": [[33, 34, 36], [65, 64]], "y": [[188, 190, 194], [192, 194]]}`
- `strokes_session_id`: Optional session ID for incremental stroke submission.

##### `MathpixClient.pdf_delete`

Deletes a PDF and all associated files from S3.

###### `MathpixClient.pdf_delete` Arguments

- `pdf_id`: The PDF ID to delete.

##### `MathpixClient.conversion_delete`

Deletes a conversion and all associated output files from S3.

###### `MathpixClient.conversion_delete` Arguments

- `conversion_id`: The conversion ID to delete.

##### `MathpixClient.app_token_new`

Creates a new app token for client-side authentication.

###### `MathpixClient.app_token_new` Arguments

- `expires`: Token expiration in seconds (30-43200, default 300). If include_strokes_session_id is True, max is 300.
- `include_strokes_session_id`: If True, creates a strokes session and returns strokes_session_id.
- `user_id`: Optional user ID to associate with this token.

##### `MathpixClient.app_token_get`

Gets information about an app token.

###### `MathpixClient.app_token_get` Arguments

- `app_token`: The app token to query.

##### `MathpixClient.app_token_delete`

Deletes an app token.

###### `MathpixClient.app_token_delete` Arguments

- `app_token`: The app token to delete.

##### `MathpixClient.scs_file_new`

Upload a file via files-api v1 for async processing. Returns an ScsFile instance.

Supports three upload modes (exactly one must be provided):

- `file_path`: Multipart upload from local file
- `url`: Upload from HTTP URL or S3 presigned URL
- `source_s3_uri`: Copy from S3 bucket (requires IAM role access)

###### `MathpixClient.scs_file_new` Arguments

- `file_path`: Path to a local file to upload.
- `url`: URL of a remote file (HTTP/HTTPS or S3 presigned URL).
- `source_s3_uri`: S3 URI (s3://bucket/key) to copy from.
- `filename`: Optional filename to use (defaults to file basename).
- `scs_job_id`: Optional job ID to group files together.
- `conversion_formats`: Dict of format names to enable (e.g., `{'mmd': True, 'docx': True}`).
- `conversion_options`: Additional conversion options dict.
- `destination_s3_uri`: Optional S3 URI to write output files.
- `destination_basename`: Optional basename for output files (defaults to file_id).
- `s3_region`: Optional AWS region for S3 operations (default us-east-1).
- `image_output_mode`: Image output mode (e.g., 'local' to upload to destination_s3_uri).
- `include_page_info`: Include page info in output (default None).
- `metadata`: Optional dict to attach metadata to the request.
- `alphabets_allowed`: Optional dict to list alphabets allowed in the output.
- `rm_spaces`: Remove extra white space from equations (default True).
- `rm_fonts`: Remove font commands from equations (default False).
- `idiomatic_eqn_arrays`: Use aligned/gathered/cases instead of array (default False).
- `include_equation_tags`: Include equation number tags in LaTeX (default False).
- `include_smiles`: Enable chemistry diagram OCR via SMILES (default True).
- `include_chemistry_as_image`: Return image crop for chemical diagrams (default False).
- `include_diagram_text`: Enable text extraction from diagrams (default False).
- `numbers_default_to_math`: Numbers are always math (default False).
- `math_inline_delimiters`: Tuple of (begin, end) delimiters for inline math.
- `math_display_delimiters`: Tuple of (begin, end) delimiters for display math.
- `page_ranges`: Page range string (e.g., "2,4-6" or "2--2").
- `enable_spell_check`: Enable predictive mode for English handwriting (default False).
- `auto_number_sections`: Auto-number sections (default False).
- `remove_section_numbering`: Remove existing section numbering (default False).
- `preserve_section_numbering`: Keep existing section numbering (default True).
- `enable_tables_fallback`: Enable advanced table processing (default False).
- `fullwidth_punctuation`: Use fullwidth Unicode punctuation (default None).

##### `MathpixClient.list_scs_files`

List files from files-api v1. Requires exactly one filter: scs_job_id or filename.

###### `MathpixClient.list_scs_files` Arguments

- `scs_job_id`: Filter by job ID.
- `filename`: Filter by filename.
- `limit`: Maximum number of results (default 100).
- `paging_state`: Optional paging state for pagination.

Returns a dict containing 'file_ids' list and 'next_page_token' for pagination.

##### `MathpixClient.list_scs_jobs`

List SCS jobs from files-api v1.

###### `MathpixClient.list_scs_jobs` Arguments

- `start`: Optional start date filter (ISO format).
- `end`: Optional end date filter (ISO format).
- `limit`: Maximum number of results (default 100).
- `paging_state`: Optional paging state for pagination.

Returns a dict containing 'jobs' list and optionally 'paging_state' for next page.

##### `MathpixClient.scs_job_status`

Get the current status of an SCS job.

###### `MathpixClient.scs_job_status` Arguments

- `scs_job_id`: The job ID to get status for.

Returns JSON response containing job status information.

##### `MathpixClient.query_usage`

Query API usage statistics.

###### `MathpixClient.query_usage` Arguments

- `from_date`: Start date for usage query (ISO 8601 format).
- `to_date`: End date for usage query (ISO 8601 format).
- `app_id`: Filter by application ID.
- `usage_type`: Filter by usage type (e.g., 'image', 'pdf-page', 'strokes-session').
- `request_args_hash`: Filter by request args hash.
- `timespan`: Aggregation period ('hour', 'day', 'month', 'year').
- `group_by`: Fields to group by (['app_id', 'usage_type', 'request_args_hash']).
- `page`: Page number (1-100, default 1).
- `per_page`: Results per page (1-1000, default 100).

Returns a dict with 'ocr_usage' list containing usage records.

##### `MathpixClient.query_ocr_results`

Query historical OCR results.

###### `MathpixClient.query_ocr_results` Arguments

- `from_date`: Start date for results query (ISO 8601 format).
- `to_date`: End date for results query (ISO 8601 format).
- `app_id`: Filter by application ID.
- `request_id`: Filter by image request ID.
- `pdf_id`: Filter by PDF ID.
- `tags`: Filter by tags (JSONB containment filter).
- `include_null_results`: Include results where result is null (default False).
- `page`: Page number (1-100, default 1).
- `per_page`: Results per page (1-1000, default 100).
- `contains_chemistry`: Filter by chemistry content detection.
- `contains_diagram`: Filter by diagram content detection.
- `is_handwritten`: Filter by handwritten content detection.
- `is_printed`: Filter by printed content detection.
- `contains_table`: Filter by table content detection.
- `contains_triangle`: Filter by triangle content detection.
- `contains_algorithm`: Filter by algorithm content detection.

Returns a dict with 'ocr_results' list.

##### `MathpixClient.query_pdf_results`

Query historical PDF results.

###### `MathpixClient.query_pdf_results` Arguments

- `from_date`: Start date for results query (ISO 8601 format).
- `to_date`: End date for results query (ISO 8601 format).
- `app_id`: Filter by application ID.
- `pdf_id`: Filter by PDF ID.
- `page`: Page number (1-1000, default 1).
- `per_page`: Results per page (1-100, default 100).

Returns a dict with 'pdfs' list.

##### `MathpixClient.query_converter_results`

Query historical converter results.

###### `MathpixClient.query_converter_results` Arguments

- `from_date`: Start date for results query (ISO 8601 format).
- `to_date`: End date for results query (ISO 8601 format).
- `app_id`: Filter by application ID.
- `page`: Page number (1-1000, default 1).
- `per_page`: Results per page (1-100, default 100).

Returns a dict with 'documents' list containing conversion results. Each document has: id, input_file, status, created_at, modified_at, request_args.

### `Pdf`

#### `Pdf` Properties

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
- `convert_to_md_zip`: Optional boolean to automatically convert your result to md.zip (markdown with local images folder)
- `convert_to_mmd_zip`: Optional boolean to automatically convert your result to mmd.zip (Mathpix markdown with local images folder)
- `convert_to_pptx`: Optional boolean to automatically convert your result to pptx (PowerPoint)
- `convert_to_html_zip`: Optional boolean to automatically convert your result to html.zip (HTML with local images folder)
- `improve_mathpix`: Optional boolean to enable Mathpix to retain user output. Default is true

#### `Pdf` Methods

- `wait_until_complete`: Wait for the PDF processing and optional conversions to complete
- `pdf_status`: Get the current status of the PDF processing
- `pdf_conversion_status`: Get the current status of the PDF conversions
- `to_docx_file`: Save the processed PDF result to a DOCX file at a local path
- `to_docx_bytes`: Get the processed PDF result as DOCX bytes
- `to_md_file`: Save the processed PDF result to a Markdown file at a local path
- `to_md_text`: Get the processed PDF result as a Markdown string
- `to_mmd_file`: Save the processed PDF result to a Mathpix Markdown file at a local path
- `to_mmd_text`: Get the processed PDF result as a Mathpix Markdown string
- `to_tex_zip_file`: Save the processed PDF result to a tex.zip file at a local path
- `to_tex_zip_bytes`: Get the processed PDF result in tex.zip format as bytes
- `to_html_file`: Save the processed PDF result to a HTML file at a local path
- `to_html_bytes`: Get the processed PDF result in HTML format as bytes
- `to_pdf_file`: Save the processed PDF result to a PDF file at a local path
- `to_pdf_bytes`: Get the processed PDF result in PDF format as bytes
- `to_lines_json_file`: Save the processed PDF line-by-line result to a JSON file at a local path
- `to_lines_json`: Get the processed PDF result in JSON format
- `to_lines_mmd_json_file`: Save the processed PDF line-by-line result, including Mathpix Markdown, to a JSON file at a local path
- `to_lines_mmd_json`: Get the processed PDF result in JSON format with text in Mathpix Markdown
- `to_md_zip_file`: Save the processed PDF result to a ZIP file containing markdown output and any embedded images
- `to_md_zip_bytes`: Get the processed PDF result in ZIPPED markdown format as bytes
- `to_mmd_zip_file`: Save the processed PDF result to a ZIP file containing Mathpix Markdown output and any embedded images
- `to_mmd_zip_bytes`: Get the processed PDF result in ZIPPED Mathpix Markdown format as bytes
- `to_pptx_file`: Save the processed PDF result to a PPTX file
- `to_pptx_bytes`: Get the processed PDF result in PPTX format as bytes
- `to_html_zip_file`: Save the processed PDF result to a ZIP file containing HTML output and any embedded images
- `to_html_zip_bytes`: Get the processed PDF result in ZIPPED HTML format as bytes

### `Image`

#### `Image` Properties

- `auth`: An Auth instance with Mathpix credentials
- `request_id`: A string storing the request_id of the image
- `file_path`: Path to a local image file, if using a local file
- `url`: URL of a remote image, if using a remote file
- `improve_mathpix`: Optional boolean to enable Mathpix to retain user output. Default is true
- `include_line_data`: Optional boolean to include line by line OCR data
- `metadata`: Optional dict to attach metadata to a request
- `is_async`: Optional boolean to enable non-interactive requests
- `result`: A Dict to containing a request's result as initially configured

#### `Image` Methods

- `results`: Get the full JSON response for the image
- `wait_until_complete`: Wait for async image processing to complete
- `lines_json`: Get line-by-line OCR data for the image
- `mmd`: Get the Mathpix Markdown (MMD) representation of the image
- `latex_styled`: Get the latex_styled representation of the image.
- `html`: Get the html representation of the image.

### `Conversion`

#### `Conversion` Properties

- `auth`: An Auth instance with Mathpix credentials.
- `conversion_id`: The unique identifier for this conversion.
- `convert_to_docx`: Optional boolean to automatically convert your result to docx
- `convert_to_md`: Optional boolean to automatically convert your result to md
- `convert_to_tex_zip`: Optional boolean to automatically convert your result to tex.zip
- `convert_to_html`: Optional boolean to automatically convert your result to html
- `convert_to_pdf`: Optional boolean to automatically convert your result to pdf
- `convert_to_latex_pdf`: Optional boolean to automatically convert your result to pdf containing LaTeX
- `convert_to_md_zip`: Optional boolean to automatically convert your result to md.zip (markdown with local images folder)
- `convert_to_mmd_zip`: Optional boolean to automatically convert your result to mmd.zip (Mathpix markdown with local images folder)
- `convert_to_pptx`: Optional boolean to automatically convert your result to pptx (PowerPoint)
- `convert_to_html_zip`: Optional boolean to automatically convert your result to html.zip (HTML with local images folder)

#### `Conversion` Methods

- `wait_until_complete`: Wait for the conversion to complete
- `conversion_status`: Get the current status of the conversion
- `to_docx_file`: Save the processed conversion result to a DOCX file at a local path
- `to_docx_bytes`: Get the processed conversion result as DOCX bytes
- `to_md_file`: Save the processed conversion result to a Markdown file at a local path
- `to_md_text`: Get the processed conversion result as a Markdown string
- `to_mmd_file`: Save the processed conversion result to a Mathpix Markdown file at a local path
- `to_mmd_text`: Get the processed conversion result as a Mathpix Markdown string
- `to_tex_zip_file`: Save the processed conversion result to a tex.zip file at a local path
- `to_tex_zip_bytes`: Get the processed conversion result in tex.zip format as bytes
- `to_html_file`: Save the processed conversion result to a HTML file at a local path
- `to_html_bytes`: Get the processed conversion result in HTML format as bytes
- `to_pdf_file`: Save the processed conversion result to a PDF file at a local path
- `to_pdf_bytes`: Get the processed conversion result in PDF format as bytes
- `to_latex_pdf_file`: Save the processed conversion result to a PDF file containing LaTeX at a local path
- `to_latex_pdf_bytes`: Get the processed conversion result in PDF format as bytes (with LaTeX)
- `to_md_zip_file`: Save the processed conversion result to a ZIP file containing markdown output and any embedded images
- `to_md_zip_bytes`: Get the processed conversion result in ZIPPED markdown format as bytes
- `to_mmd_zip_file`: Save the processed conversion result to a ZIP file containing Mathpix Markdown output and any embedded images
- `to_mmd_zip_bytes`: Get the processed conversion result in ZIPPED Mathpix Markdown format as bytes
- `to_pptx_file`: Save the processed conversion result to a PPTX file
- `to_pptx_bytes`: Get the processed conversion result in PPTX format as bytes
- `to_html_zip_file`: Save the processed PDF result to a ZIP file containing HTML output and any embedded images
- `to_html_zip_bytes`: Get the processed PDF result in ZIPPED HTML format as bytes

### `Batch`

#### `Batch` Properties

- `auth`: An Auth instance with Mathpix credentials.
- `batch_id`: The unique identifier for this batch.

#### `Batch` Methods

- `status`: Get the current status of the batch, including keys and results.
- `wait_until_complete`: Wait for all items in the batch to complete processing.
- `results`: Get the results dict mapping url_key to OCR result for each processed item.
- `keys`: Get the list of URL keys in this batch.

### `ScsFile`

#### `ScsFile` Properties

- `auth`: An Auth instance with Mathpix credentials.
- `file_id`: The unique identifier for this file.

#### `ScsFile` Methods

- `status`: Get the current status of the file processing (file_id, status, num_pages, num_pages_completed, percent_done, formats).
- `wait_until_complete`: Wait for the file processing to complete.
- `wait_for_format`: Wait for a specific format conversion to complete.
- `to_mmd_text`: Get the processed file result as Mathpix Markdown string.
- `to_md_text`: Get the processed file result as Markdown string.
- `to_tex_text`: Get the processed file result as LaTeX string.
- `to_docx_bytes`: Get the processed file result as DOCX bytes.
- `to_xlsx_bytes`: Get the processed file result as XLSX bytes.
- `to_pptx_bytes`: Get the processed file result as PPTX bytes.
- `to_pdf_bytes`: Get the processed file result as PDF bytes.
- `to_latex_pdf_bytes`: Get the processed file result as LaTeX-rendered PDF bytes.
- `to_html_bytes`: Get the processed file result as HTML bytes.
- `to_tex_zip_bytes`: Get the processed file result as tex.zip bytes.
- `to_md_zip_bytes`: Get the processed file result as md.zip bytes.
- `to_mmd_zip_bytes`: Get the processed file result as mmd.zip bytes.
- `to_html_zip_bytes`: Get the processed file result as html.zip bytes.
- `to_jpg_bytes`: Get the processed file result as JPG bytes.
- `to_png_bytes`: Get the processed file result as PNG bytes.
- `to_lines_json`: Get the processed file result as lines.json.
- `to_lines_mmd_json`: Get the processed file result as lines.mmd.json.
- `to_mmd_file`: Save the processed file result to a MMD file at a local path.
- `to_md_file`: Save the processed file result to a Markdown file at a local path.
- `to_docx_file`: Save the processed file result to a DOCX file at a local path.
- `to_xlsx_file`: Save the processed file result to an XLSX file at a local path.
- `to_pptx_file`: Save the processed file result to a PPTX file at a local path.
- `to_pdf_file`: Save the processed file result to a PDF file at a local path.
- `to_html_file`: Save the processed file result to an HTML file at a local path.
- `to_tex_zip_file`: Save the processed file result to a tex.zip file at a local path.
- `cropped_image`: Get a cropped region from a specific page as JPEG bytes.

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

## Development

```bash
# Clone the repository
git clone git@github.com:Mathpix/mpxpy.git
cd mpxpy

# Install in development mode
pip install -e .
# Or install using the requirements.txt file
pip install -r requirements.txt
```

### Running Tests

To run tests you will need to add [authentication](#authentication).

```bash
# Install test dependencies
pip install -e ".[dev]"
# Or install using the requirements.txt file
pip install -r requirements.txt
# Run tests
pytest
```

### Logging

To configure the logger level, which is set at `INFO` by default, set the MATHPIX_LOG_LEVEL env variable to the desired logger level.

- `DEBUG`: logs all events, including polling events
- `INFO`: logs all events except for polling events

```bash
MATHPIX_LOG_LEVEL=DEBUG
```
