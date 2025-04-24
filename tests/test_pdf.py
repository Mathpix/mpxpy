import os
import shutil
import pytest
from mpxpy.mathpix_client import MathpixClient

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()


def test_pdf_convert_remote_file(client):
    pdf_file_url = "http://cs229.stanford.edu/notes2020spring/cs229-notes1.pdf"
    pdf_file = client.pdf_new(
        file_url=pdf_file_url,
        webhook_url="http://gateway:8080/webhook/convert-api",
        mathpix_webhook_secret="test-secret",
        webhook_payload={
            "data": "test data"
        },
        webhook_enabled_events=["pdf_processing_complete"],
    )
    assert pdf_file.pdf_id is not None
    assert pdf_file.wait_until_complete(timeout=60)
    status = pdf_file.pdf_status()
    assert status['status'] == 'completed'

def test_pdf_convert_remote_file_to_docx(client):
    pdf_file_url = "http://cs229.stanford.edu/notes2020spring/cs229-notes1.pdf"
    pdf_file = client.pdf_new(
        file_url=pdf_file_url,
        webhook_url="http://gateway:8080/webhook/convert-api",
        mathpix_webhook_secret="test-secret",
        webhook_payload={
            "data": "test data"
        },
        webhook_enabled_events=["pdf_processing_complete"],
        conversion_formats={
            "docx": True
        }
    )
    assert pdf_file.pdf_id is not None
    assert pdf_file.wait_until_complete(timeout=60)
    status = pdf_file.pdf_status()
    assert status['status'] == 'completed'


def test_pdf_convert_local_file(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/sample.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    pdf_file = client.pdf_new(
        file_path=pdf_file_path,
        webhook_url="http://gateway:8080/webhook/convert-api",
        mathpix_webhook_secret="test-secret",
        webhook_payload={
            "data": "test data"
        },
        webhook_enabled_events=["pdf_processing_complete"],
        conversion_formats={
            "docx": True
        }
    )
    assert pdf_file.pdf_id is not None
    assert pdf_file.wait_until_complete(timeout=60)
    status = pdf_file.pdf_status()
    assert status['status'] == 'completed'


def test_pdf_download_conversion(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/the-internet-tidal-wave.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    pdf_file = client.pdf_new(
        file_path=pdf_file_path,
        webhook_url="http://gateway:8080/webhook/convert-api",
        mathpix_webhook_secret="test-secret",
        webhook_payload={
            "data": "test data"
        },
        webhook_enabled_events=["pdf_processing_complete"],
        conversion_formats={
            "docx": True
        }
    )
    assert pdf_file.pdf_id is not None
    completed = pdf_file.wait_until_complete(timeout=60)
    assert completed
    output_dir = 'output'
    os.mkdir(output_dir)
    file_path = pdf_file.download_output_to_local_path('docx', output_dir)
    assert os.path.exists(file_path)
    if output_dir and os.path.isdir(output_dir):
        shutil.rmtree(output_dir)


def test_pdf_get_result_bytes(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/theres-plenty-of-room-at-the-bottom.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    pdf_file = client.pdf_new(
        file_path=pdf_file_path,
        webhook_url="http://gateway:8080/webhook/convert-api",
        mathpix_webhook_secret="test-secret",
        webhook_payload={
            "data": "test data"
        },
        webhook_enabled_events=["pdf_processing_complete"],
        conversion_formats={
            "docx": True
        }
    )
    assert pdf_file.pdf_id is not None
    assert pdf_file.wait_until_complete(timeout=60)
    raw = pdf_file.download_output('md')
    assert raw is not None


if __name__ == '__main__':
    # test_pdf_convert_remote_file(client())
    # test_pdf_convert_local_file(client())
    # test_pdf_download_conversion(client())
    # test_pdf_get_result_bytes(client())
    client = MathpixClient()
    pdf = client.pdf_new(file_url="http://localhost:0000")
    print(pdf.pdf_id)
    pdf.wait_until_complete(timeout=10)
    print(pdf.pdf_status())