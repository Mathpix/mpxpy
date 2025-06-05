# mpxpy changelog

## June 5, 2025

- Add improve_mathpix argument to the Client, Image, and Pdf classes
  - Any new requests will defer to the Client's improve_mathpix setting if it is set to False

## May 19, 2025

- Create change log file
- Add pytest to pyproject dev dependencies for installation with `pip install -e ".[dev]"`
- Create requirements.txt file for development