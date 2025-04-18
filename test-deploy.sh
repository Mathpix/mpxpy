#!/bin/bash
# Script to build and upload the package to TestPyPI

set -e
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/
echo "--- Building package ---"
python -m build
echo "--- Uploading to TestPyPI ---"
python -m twine upload --repository testpypi -u __token__ dist/*
echo "--- Successfully uploaded to TestPyPI! ---"