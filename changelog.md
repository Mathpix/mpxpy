# mpxpy changelog

## July 23, 2026

- Support the public Files API v1
  - `file_new` submits a single document, taking exactly one of `source_uri` (a remote `s3://`, `gs://`, public `https://`, or Azure Blob URI, via `POST /files/v1/uri`) or `file_path` (a local file, via multipart `POST /files/v1`); supports `Idempotency-Key` retry safety, `(job_id, custom_id)` idempotency (remote submissions only), and the `filename`, `s3_region`, and `include_page_info` options
  - `file_job_new` submits documents in bulk (server-enforced per-call ceiling, currently 200,000) via `POST /files/v1/jobs`; the new `FileJob` class polls job status, lists files with a status filter and pagination iterator, and fetches files by `custom_id`
  - `file_job_list`, `file_get`, `file_delete`, and `file_job_get` cover the jobs listing and file lifecycle endpoints; the `*_get` methods fetch the resource and return a seeded handle, raising `FilesApiError` for unknown ids
  - New `File` class adds `delete()` and lazy status attributes, raises on failed status requests, and disambiguates download errors per the public API (`format_not_ready` vs `not_found` vs `unsupported_format`)
  - New `FilesApiError` exception carries the Files API error code (`error_id`) and HTTP status; it is raised only for responses with a recognizable Files API error body, other failures raise `MathpixClientError`
  - In `file_new` and `file_job_new`, `conversion_options` may no longer override the validated request fields (`source_uri`, `files`, `job_id`, `custom_id`, `metadata`)
  - The client no longer duplicates server-enforced constraints (identifier charset/length, items-per-call ceiling, status filter values); the server's `FilesApiError` is authoritative for those
  - `ScsFile`, `scs_file_new`, `list_scs_files`, `list_scs_jobs`, and `scs_job_status` are deprecated. `scs_file_new` is now a thin wrapper that translates its legacy argument names and forwards to `file_new`; the listing/status methods keep their legacy endpoints and response shapes during the deprecation window. Migrate to `File`, `file_new`, `file_job_get(job_id).files()`, `file_job_list`, and `file_job_get(job_id).status()`
  - Data Sources API: `onboarding_identities`, `data_source_new`, `data_sources_list`, `data_source_get`, `data_source_test`, and `data_source_delete` register and manage cloud storage (S3, GCS, Azure Blob) for use as `source_uri`/`destination_uri`; new `DataSource` class with `test()` and `delete()`
  - Debug logging redacts remote URIs to scheme and host, since signed URLs carry credentials in their query strings
- All requests now send a `User-Agent: mpxpy/<version>` header

## June 5, 2025

- Add improve_mathpix argument to the Client, Image, and Pdf classes
  - Any new requests will defer to the Client's improve_mathpix setting if it is set to False

## May 19, 2025

- Create change log file
- Add pytest to pyproject dev dependencies for installation with `pip install -e ".[dev]"`
- Create requirements.txt file for development