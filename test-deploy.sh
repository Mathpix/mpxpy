#!/bin/bash
# Script to build and upload the package to TestPyPI

set -e

echo "--- Cleaning up previous builds ---"
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/

echo ""
echo "--- Building package ---"
python -m build

echo ""
echo "--- Uploading to TestPyPI ---"
echo "You will be prompted for your TestPyPI credentials."
python -m twine upload --repository testpypi -u __token__ dist/*

echo ""
echo "--- Successfully uploaded to TestPyPI! ---"
echo "Verify at: https://test.pypi.org/project/mathpix/"
echo "Test installation using: python -m pip install --index-url https://test.pypi.org/simple/ --no-deps mathpix"