"""Unit tests for v3 request option forwarding and conflict handling."""
import json
from unittest.mock import patch
import pytest
from mpxpy.errors import ValidationError
from mpxpy.mathpix_client import MathpixClient


@pytest.fixture
def client() -> MathpixClient:
    return MathpixClient(app_id='test-app', app_key='test-key')


def test_image_new_sends_documented_and_extra_options(client: MathpixClient, tmp_path) -> None:
    image_path = tmp_path / 'image.png'
    image_path.write_bytes(b'image')
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value.json.return_value = {'request_id': 'image-1'}
        client.image_new(
            file_path=str(image_path),
            disable_itemize=False,
            disable_lstlisting=True,
            include_page_info=False,
            enable_document_layout=True,
            extra_options={'future_image_option': 'enabled'},
        )
    options = json.loads(mock_post.call_args.kwargs['data']['options_json'])
    assert {
        key: options[key] for key in (
            'disable_itemize', 'disable_lstlisting', 'include_page_info',
            'enable_document_layout', 'future_image_option',
        )
    } == {
        'disable_itemize': False,
        'disable_lstlisting': True,
        'include_page_info': False,
        'enable_document_layout': True,
        'future_image_option': 'enabled',
    }


def test_image_new_rejects_modeled_extra_options(client: MathpixClient) -> None:
    for key in ('src', 'metadata', 'callback', 'disable_itemize'):
        with pytest.raises(ValidationError):
            client.image_new(url='https://example.com/image.png', extra_options={key: 'override'})


def test_pdf_new_sends_documented_and_extra_options(client: MathpixClient, tmp_path) -> None:
    pdf_path = tmp_path / 'document.pdf'
    pdf_path.write_bytes(b'%PDF-1.4')
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value.json.return_value = {'pdf_id': 'pdf-1'}
        client.pdf_new(
            file_path=str(pdf_path),
            disable_itemize=False,
            disable_lstlisting=True,
            include_page_info=True,
            include_page_breaks=False,
            conversion_options={'docx': {'font_size': 12}},
            extra_options={'future_pdf_option': 'enabled'},
        )
    options = json.loads(mock_post.call_args.kwargs['data']['options_json'])
    assert {
        key: options[key] for key in (
            'disable_itemize', 'disable_lstlisting', 'include_page_info',
            'include_page_breaks', 'conversion_options', 'future_pdf_option',
        )
    } == {
        'disable_itemize': False,
        'disable_lstlisting': True,
        'include_page_info': True,
        'include_page_breaks': False,
        'conversion_options': {'docx': {'font_size': 12}},
        'future_pdf_option': 'enabled',
    }


def test_pdf_new_rejects_modeled_extra_options(client: MathpixClient) -> None:
    for key in (
            'url', 'metadata', 'conversion_formats', 'file_batch_id', 'webhook_url',
            'mathpix_webhook_secret', 'webhook_payload', 'webhook_enabled_events',
            'conversion_options',
    ):
        with pytest.raises(ValidationError):
            client.pdf_new(url='https://example.com/document.pdf', extra_options={key: 'override'})


def test_conversion_new_sends_documented_and_extra_options(client: MathpixClient) -> None:
    with patch('mpxpy.mathpix_client.post') as mock_post:
        mock_post.return_value.json.return_value = {'conversion_id': 'conversion-1'}
        client.conversion_new(
            mmd='# Document',
            convert_to_docx=True,
            conversion_options={'docx': {'font_size': 12}},
            extra_options={'metadata': {'customer_id': 'customer-1'}},
        )
    assert mock_post.call_args.kwargs['json'] == {
        'mmd': '# Document',
        'formats': {'docx': True},
        'conversion_options': {'docx': {'font_size': 12}},
        'metadata': {'customer_id': 'customer-1'},
    }


def test_conversion_new_rejects_modeled_extra_options(client: MathpixClient) -> None:
    for key in ('mmd', 'formats', 'conversion_options'):
        with pytest.raises(ValidationError):
            client.conversion_new(
                mmd='# Document',
                convert_to_docx=True,
                extra_options={key: 'override'},
            )
