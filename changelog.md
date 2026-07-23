# mpxpy changelog

## July 23, 2026

- Support the public Files API v1
  - `file_new` submits a single document by remote URI (`s3://`, `gs://`, public `https://`, Azure Blob) via `POST /files/v1/uri`; supports `Idempotency-Key` retry safety, `(job_id, custom_id)` idempotency, and the `filename`, `s3_region`, and `include_page_info` options
  - `file_job_new` submits up to 200,000 documents in one call via `POST /files/v1/jobs`; the new `FileJob` class polls job status, lists files with a status filter and pagination iterator, and fetches files by `custom_id`
  - `file_jobs_list`, `file_get`, `file_delete`, and `file_job_get` cover the jobs listing and file lifecycle endpoints
  - New `File` class adds `delete()` and lazy status attributes, raises on failed status requests, and disambiguates download errors per the public API (`format_not_ready` vs `not_found` vs `unsupported_format`)
  - New `FilesApiError` exception carries the Files API error code (`error_id`) and HTTP status; it is raised only for responses with a recognizable Files API error body, other failures raise `MathpixClientError`
  - In `file_new` and `file_job_new`, `conversion_options` may no longer override the validated request fields (`source_uri`, `files`, `job_id`, `custom_id`, `metadata`)
  - `ScsFile`, `scs_file_new`, `list_scs_files`, `list_scs_jobs`, and `scs_job_status` are deprecated but keep their legacy behavior during the deprecation window, except that `scs_file_new` remote submissions (`url`/`source_s3_uri`) forward to the public `POST /files/v1/uri` endpoint and the private `ScsFile.cropped_image()` helper is removed. Migrate to `File`, `file_new`, `file_job_get(job_id).files()`, `file_jobs_list`, and `file_job_get(job_id).status()`
  - Data Sources API: `onboarding_identities`, `data_source_new` (with `exist_ok` conflict resolution), `data_sources_list`, `data_source_get`, `data_source_test`, and `data_source_delete` register and manage cloud storage (S3, GCS, Azure Blob) for use as `source_uri`/`destination_uri`; new `DataSource` class with `test()` and `delete()`
- All requests now send a `User-Agent: mpxpy/<version>` header

## June 5, 2025

- Add improve_mathpix argument to the Client, Image, and Pdf classes
  - Any new requests will defer to the Client's improve_mathpix setting if it is set to False

## May 19, 2025

- Create change log file
- Add pytest to pyproject dev dependencies for installation with `pip install -e ".[dev]"`
- Create requirements.txt file for development