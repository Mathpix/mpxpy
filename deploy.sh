#!/bin/bash
# Script to build and upload the package to the OFFICIAL PyPI

set -e

echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "!!!       DEPLOYING MATHPIX TO OFFICIAL PyPI        !!!"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "This will upload the package publicly."
echo ""

read -p "Are you sure you want to proceed with deploying Mathpix to PyPI? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Deployment cancelled."
    exit 1
fi

echo ""
echo "--- Cleaning up previous builds ---"
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/

echo ""
echo "--- Building package ---"
python -m build

echo ""
echo "--- Uploading to PyPI (production) ---"
python -m twine upload -u __token__ dist/*

echo ""
echo "--- Successfully uploaded to PyPI! ---"
echo "Verify at: https://pypi.org/project/mathpix/"
echo "Install using: python -m pip install mathpix"
