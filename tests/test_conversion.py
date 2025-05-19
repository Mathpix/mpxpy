import os
import pytest
import shutil
from mpxpy.mathpix_client import MathpixClient
from mpxpy.errors import ValidationError, ConversionIncompleteError

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()

def test_no_format_conversion(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    with pytest.raises(ValidationError):
        client.conversion_new(mmd=mmd)

def test_conversion(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, convert_to_docx=True)
    assert conversion.conversion_id is not None
    conversion.wait_until_complete(timeout=10)
    status = conversion.conversion_status()
    assert status['status'] == 'completed'

def test_conversion_get_result_docx(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, convert_to_docx=True)
    assert conversion.conversion_id is not None
    conversion.wait_until_complete(timeout=10)
    docx_bytes = conversion.to_docx_bytes()
    assert docx_bytes is not None
    assert len(docx_bytes) > 0
    assert docx_bytes.startswith(b'PK') # Test whether it matches the DOCX file signature

def test_conversion_save_docx_to_local_path(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, convert_to_docx=True)
    assert conversion.conversion_id is not None
    output_dir = 'output'
    output_name = 'result.docx'
    output_path = os.path.join(output_dir, output_name)
    try:
        conversion.wait_until_complete(timeout=10)
        path = conversion.to_docx_file(path=output_path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            shutil.rmtree(output_dir)

def test_conversion_bad_timeout(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, convert_to_docx=True)
    with pytest.raises(ValidationError):
        conversion.wait_until_complete(timeout=0)

def test_conversion_incomplete_conversion(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, convert_to_docx=True)
    with pytest.raises(ConversionIncompleteError):
        conversion.to_docx_bytes()

if __name__ == '__main__':
    client = MathpixClient()