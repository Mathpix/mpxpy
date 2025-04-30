import os
import shutil
import pytest

from mpxpy.errors import ConversionIncompleteError, ValidationError
from mpxpy.mathpix_client import MathpixClient

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()


def test_pdf_convert_remote_file(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf_file = client.pdf_new(
        file_url=pdf_file_url,
    )
    assert pdf_file.pdf_id is not None
    assert pdf_file.wait_until_complete(timeout=60)
    status = pdf_file.pdf_status()
    assert status['status'] == 'completed'

def test_pdf_convert_remote_file_to_docx(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf_file = client.pdf_new(
        file_url=pdf_file_url,
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
        conversion_formats={
            "docx": True
        }
    )
    assert pdf_file.pdf_id is not None
    assert pdf_file.wait_until_complete(timeout=60)
    raw = pdf_file.download_output('md')
    assert raw is not None

def test_pdf_download_to_local_path(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf = client.pdf_new(
        file_url=pdf_file_url,
        conversion_formats={
            "docx": True
        }
    )
    assert pdf.pdf_id is not None
    output_dir = pdf.pdf_id
    try:
        pdf.wait_until_complete(timeout=10)
        path = pdf.download_output_to_local_path('docx', path=output_dir)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            shutil.rmtree(output_dir)

def test_pdf_download_output_incomplete_conversion(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf_file = client.pdf_new(
        file_url=pdf_file_url,
        conversion_formats={
            "docx": True
        }
    )
    with pytest.raises(ConversionIncompleteError):
        pdf_file.download_output(conversion_format='docx')

def test_invalid_pdf_arguments(client):
    pdf_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/bitcoin-7.pdf"
    pdf_file_path = os.path.join(current_dir, "files/pdfs/theres-plenty-of-room-at-the-bottom.pdf")
    assert os.path.exists(pdf_file_path), f"Test input file not found: {pdf_file_path}"
    with pytest.raises(ValidationError):
        pdf = client.pdf_new(file_path=pdf_file_path, file_url=pdf_file_url)

def test_bad_pdf_path(client):
    pdf_file_path = os.path.join(current_dir, "files/pdfs/nonexistent.pdf")
    with pytest.raises(FileNotFoundError):
        pdf = client.pdf_new(file_path=pdf_file_path)


if __name__ == '__main__':
    client = MathpixClient(api_url='http://localhost:8070')
    # test_pdf_convert_remote_file(client)
    # test_pdf_convert_remote_file_to_docx(client)
    # test_pdf_convert_local_file(client)
    # test_pdf_download_conversion(client)
    # test_pdf_get_result_bytes(client)

    # pdf = client.pdf_new(file_path='tests/files/pdfs/theres-plenty-of-room-at-the-bottom.pdf', file_batch_uuid='helloworld')
    # pdf.wait_until_complete()
    # pdf.download_output_to_local_path(conversion_format='lines.json', path='outputs/')

    import os

    file_batch = client.file_batch_new()
    print(f'file_batch_uuid: {file_batch.file_batch_uuid}')
    input_folder = "tests/files/pdfs"
    output_folder = "outputs"
    os.makedirs(output_folder, exist_ok=True)
    for filename in os.listdir(input_folder):
        file_path = os.path.join(input_folder, filename)
        print(file_path)
        pdf = client.pdf_new(file_path=file_path, file_batch_uuid=file_batch.file_batch_uuid)
    file_batch.wait_until_complete(timeout=200)
    print(file_batch.file_batch_status())
    # file_batch.wait_until_complete(timeout=500)
    # response = file_batch.files()
    # pdfs = response['files']
    # for pdf in pdfs:
    #     pdf.download_output_to_local_path(conversion_format='pdf', path=f'{output_folder}/{pdf.pdf_id}.pdf')