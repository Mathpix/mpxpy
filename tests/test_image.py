import os
import shutil
import pytest

from mpxpy.errors import ValidationError
from mpxpy.mathpix_client import MathpixClient

current_dir = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def client():
    return MathpixClient()


def test_image_conversion_remote_file(client):
    image_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/cases_hw.jpg"
    image = client.image_new(
        url=image_file_url,
    )
    lines_result = image.lines_json()
    assert lines_result is not None
    mmd_result = image.mmd()
    assert mmd_result is not None
    assert isinstance(mmd_result, str)


def test_image_conversion_local_file(client):
    """Tests processing a local image file."""
    image_file_path = os.path.join(current_dir, "files/images/code_5.jpg")
    assert os.path.exists(image_file_path), f"Test input file not found: {image_file_path}"
    image = client.image_new(
        file_path=image_file_path
    )
    mmd_result = image.mmd()
    assert mmd_result is not None
    assert isinstance(mmd_result, str)


def test_conversion_from_image_output(client):
    image_file_path = os.path.join(current_dir, "files/images/cases_hw.png")
    assert os.path.exists(image_file_path), f"Test input file not found: {image_file_path}"
    image = client.image_new(
        file_path=image_file_path
    )
    mmd = image.mmd()
    assert mmd is not None and len(mmd) > 0
    conversion = client.conversion_new(mmd=mmd, convert_to_docx=True)
    completed = conversion.wait_until_complete(timeout=20)
    assert completed, "Conversion from MMD did not complete"
    output_dir = "output"
    output_file = 'cases_hw.docx'
    output_path = os.path.join(output_dir, output_file)
    os.mkdir(output_dir)
    file_path_obj = conversion.to_docx_file(path=output_path)
    file_path_str = str(file_path_obj)
    assert os.path.exists(file_path_str), f"Downloaded file does not exist at {file_path_str}"
    assert os.path.getsize(file_path_str) > 0, f"Downloaded file {file_path_str} is empty"
    if output_dir and os.path.isdir(output_dir):
        shutil.rmtree(output_dir)

def test_invalid_image_arguments(client):
    image_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/cases_hw.jpg"
    image_file_path = os.path.join(current_dir, "files/images/cases_hw.png")
    assert os.path.exists(image_file_path), f"Test input file not found: {image_file_path}"
    with pytest.raises(ValidationError):
        client.image_new(file_path=image_file_path, url=image_file_url)


if __name__ == '__main__':
    client = MathpixClient()