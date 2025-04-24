import os
import pytest
import shutil
from mpxpy.mathpix_client import MathpixClient
from mpxpy.errors import MathpixClientError, ValidationError, ConversionIncompleteError

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()


def test_convert_mmd(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, conversion_formats={'docx': True})
    assert conversion.conversion_id is not None
    conversion.wait_until_complete(timeout=10)
    status = conversion.conversion_status()
    assert status['status'] == 'completed'

def test_convert_mmd_download(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, conversion_formats={'docx': True})
    assert conversion.conversion_id is not None
    conversion.wait_until_complete(timeout=10)
    content = conversion.download_output('docx')
    assert content is not None
    assert len(content) > 0
    assert content.startswith(b'PK') # Test whether it matches the DOCX file signature

def test_convert_mmd_download_to_local(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, conversion_formats={'docx': True})
    assert conversion.conversion_id is not None
    output_dir = conversion.conversion_id
    try:
        conversion.wait_until_complete(timeout=10)
        path = conversion.download_output_to_local_path('docx', path=output_dir)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            shutil.rmtree(output_dir)


def test_convert_mmd_bad_conversion_format(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    with pytest.raises(MathpixClientError):
        client.conversion_new(mmd=mmd, conversion_formats={'latex': True})

def test_convert_mmd_bad_timeout(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, conversion_formats={'docx': True})
    with pytest.raises(ValidationError):
        conversion.wait_until_complete(timeout=0)

def test_convert_mmd_incomplete_conversion(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, conversion_formats={'docx': True})
    with pytest.raises(ConversionIncompleteError):
        conversion.download_output(conversion_format='docx')

if __name__ == '__main__':
    client = MathpixClient()
    # test_convert_mmd(client)
    # test_convert_mmd_download(client)
    # test_convert_mmd_download_to_local(client)