import glob
import pytest
from mpxpy.mathpix_client import MathpixClient

@pytest.fixture
def client():
    return MathpixClient()


def process_pdf_folder(client):
    file_batch = client.file_batch_new()
    pdf_folder_path = "./files/pdfs/"
    # pdf_folder_path = "./files/file-batch-with-invalid-pdfs/"
    pdf_file_list = glob.glob(pdf_folder_path + "*.*")
    pdf_file_list = pdf_file_list[:2]
    print(pdf_file_list)
    for pdf_file_path in pdf_file_list:
        print("Sending file: {}".format(pdf_file_path))
        client.pdf_new(
            file_path=pdf_file_path,
            file_batch_id=file_batch.file_batch_id,
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
    print(file_batch.file_batch_status())
    file_batch.wait_until_complete(timeout=60)
    print(file_batch.file_batch_status())
    cursor=None
    while True:
        print("Fetching page of pdf IDs...")
        files_list = file_batch.files(cursor=cursor)
        for file in files_list["files"]:
            print(file.pdf_id)
            # file.download_output_to_local_path('docx', 'outputs')
        if not files_list["has_more"]:
            break
        else:
            cursor = files_list["cursor"]

"""
    for pdf_id in completed_pdfs:
        GET v3/pdf/{pdf_id}.mmd
        GET v3/pdf/{pdf_id}.lines.json
        writeToBucket(path_to_file/pdf_id.
"""

if __name__ == '__main__':
    process_pdf_folder(client())