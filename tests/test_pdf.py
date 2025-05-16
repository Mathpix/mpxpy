import os
import shutil
from typing import Dict

import pytest

from mpxpy.errors import ConversionIncompleteError, ValidationError
from mpxpy.mathpix_client import MathpixClient

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()


def test_pdf_convert_remote_file(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf = client.pdf_new(
        url=pdf_file_url
    )
    assert pdf.pdf_id is not None
    assert pdf.wait_until_complete(timeout=60)
    status = pdf.pdf_status()
    assert status['status'] == 'completed'

def test_pdf_convert_remote_file_to_docx(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf = client.pdf_new(
        url=pdf_file_url,
        convert_to_md=True
    )
    assert pdf.pdf_id is not None
    assert pdf.wait_until_complete(timeout=60)
    status = pdf.pdf_status()
    assert status['status'] == 'completed'


def test_pdf_convert_local_file(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/sample.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    pdf = client.pdf_new(
        file_path=pdf_file_path,
        convert_to_md=True
    )
    assert pdf.pdf_id is not None
    assert pdf.wait_until_complete(timeout=60)
    status = pdf.pdf_status()
    assert status['status'] == 'completed'


def test_pdf_save_md_to_local_path(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/the-internet-tidal-wave.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    pdf = client.pdf_new(
        file_path=pdf_file_path,
        convert_to_md=True
    )
    assert pdf.pdf_id is not None
    completed = pdf.wait_until_complete(timeout=60)
    assert completed
    output_dir = 'output'
    output_name = 'the-internet-tidal-wave.md'
    output_path = os.path.join(output_dir, output_name)
    file_path = pdf.to_md_file(path=output_path)
    try:
        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) > 0
    finally:
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            shutil.rmtree(output_dir)


def test_pdf_get_result_md_text(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/theres-plenty-of-room-at-the-bottom.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    pdf = client.pdf_new(
        file_path=pdf_file_path,
        convert_to_md=True
    )
    assert pdf.pdf_id is not None
    assert pdf.wait_until_complete(timeout=60)
    md_output = pdf.to_md_text()
    assert md_output is not None
    assert isinstance(md_output, str), f"Expected md output to be a string, got {type(md_output)}"

def test_pdf_get_result_lines_json(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/sample.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    pdf = client.pdf_new(
        file_path=pdf_file_path
    )
    assert pdf.pdf_id is not None
    assert pdf.wait_until_complete(timeout=60)
    lines_json = pdf.to_lines_json()
    assert lines_json is not None
    assert isinstance(lines_json, Dict), f"Expected lines.json output to be a dict, got {type(lines_json)}"

def test_pdf_get_result_docx(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/sample.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    pdf = client.pdf_new(
        file_path=pdf_file_path,
        convert_to_docx=True
    )
    assert pdf.pdf_id is not None
    assert pdf.wait_until_complete(timeout=60)
    docx_bytes = pdf.to_docx_bytes()
    assert docx_bytes is not None
    assert isinstance(docx_bytes, bytes), f"Expected docx output to be of type bytes, got {type(docx_bytes)}"


def test_pdf_download_output_incomplete_conversion(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf = client.pdf_new(
        url=pdf_file_url,
        convert_to_md=True
    )
    with pytest.raises(ConversionIncompleteError):
        pdf.to_md_text()

def test_invalid_pdf_arguments(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf_file_path = os.path.join(current_dir, "files/pdfs/theres-plenty-of-room-at-the-bottom.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    with pytest.raises(ValidationError):
        client.pdf_new(file_path=pdf_file_path, url=pdf_file_url)

def test_bad_pdf_path(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/nonexistent.pdf")
    with pytest.raises(FileNotFoundError):
        client.pdf_new(file_path=pdf_file_path)


if __name__ == '__main__':
    client = MathpixClient()