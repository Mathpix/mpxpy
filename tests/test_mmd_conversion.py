import os
import time
import pytest
from mpxpy.mathpix_client import MathpixClient

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()


def test_pdf_convert_remote_file(client):
    image_file_url = "https://mathpix-ocr-examples.s3.amazonaws.com/cases_hw.jpg"
    image_file = client.image_new(
        file_url=image_file_url,
    )
    mmd_result = image_file.mmd()
    conversion = client.conversion_new(mmd=mmd_result, formats={'docx': True})
    conversion.wait_until_complete(timeout=30)
    print(conversion.conversion_status())

if __name__ == '__main__':
    client = MathpixClient()
    print(client.auth.api_url)
    print(client.auth.headers)
    test_pdf_convert_remote_file(client)