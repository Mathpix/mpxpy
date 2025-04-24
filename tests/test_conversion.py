import os
import pytest
from mpxpy.mathpix_client import MathpixClient

current_dir = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def client():
    return MathpixClient()


def test_convert_mmd(client):
    mmd = '''
    \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
    '''
    conversion = client.conversion_new(mmd=mmd, conversion_formats={'docx': True})
    print(conversion)
    conversion.wait_until_complete(timeout=10)
    print(conversion.conversion_status())

if __name__ == '__main__':
    client = MathpixClient()
    # test_convert_mmd(client)
    mmd = '''
        \( f(x)=\left\{\begin{array}{ll}x^{2} & \text { if } x<0 \\ 2 x & \text { if } x \geq 0\end{array}\right. \)
        '''
    conversion = client.conversion_new(mmd=mmd, conversion_formats={'docx': True})
    conversion.wait_until_complete(timeout=10)
    conversion.download_output_to_local_path('docx', path='output/dir')
