import os
import shutil
import pytest
from mpxpy.mathpix_client import MathpixClient

current_dir = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def client():
    return MathpixClient()


def test_simple_image_convert_remote_file(client):
    image_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/cases_hw.jpg"
    image_file = client.image_new(
        file_url=image_file_url,
    )
    lines_result = image_file.lines_json()
    assert lines_result is not None
    mmd_result = image_file.mmd()
    assert mmd_result is not None
    assert isinstance(mmd_result, str)


def test_simple_image_convert_local_file(client):
    """Tests processing a local image file."""
    image_file_path = os.path.join(current_dir, "files/images/code_5.jpg")
    assert os.path.exists(image_file_path), f"Test input file not found: {image_file_path}"
    image_file = client.image_new(
        file_path=image_file_path
    )
    mmd_result = image_file.mmd()
    assert mmd_result is not None
    assert isinstance(mmd_result, str)


def test_simple_conversion_from_image_output(client):
    image_file_path = os.path.join(current_dir, "files/images/cases_hw.png")
    assert os.path.exists(image_file_path), f"Test input file not found: {image_file_path}"
    image_file = client.image_new(
        file_path=image_file_path
    )
    mmd = image_file.mmd()
    assert mmd is not None and len(mmd) > 0
    conversion = client.conversion_new(mmd=mmd, conversion_formats={"docx": True})
    completed = conversion.wait_until_complete(timeout=20)
    assert completed, "Conversion from MMD did not complete"
    output_dir = "output"
    os.mkdir(output_dir)
    file_path_obj = conversion.download_output_to_local_path("docx", output_dir)
    file_path_str = str(file_path_obj)
    assert os.path.exists(file_path_str), f"Downloaded file does not exist at {file_path_str}"
    assert os.path.getsize(file_path_str) > 0, f"Downloaded file {file_path_str} is empty"
    if output_dir and os.path.isdir(output_dir):
        shutil.rmtree(output_dir)


if __name__ == '__main__':
    client = MathpixClient()
    # test_simple_image_convert_remote_file(client)
    # test_simple_image_convert_local_file(client)
    # test_simple_conversion_from_image_output(client)