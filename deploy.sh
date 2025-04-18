#!/bin/bash
# Script to build and upload mpxpy to PyPI

set -e
echo "DEPLOYING mpxpy TO OFFICIAL PyPI"
read -p "Are you sure you want to proceed with deploying mpxpy to PyPI? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Deployment cancelled."
    exit 1
fi
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/
echo "--- Building package ---"
python -m build
echo "--- Uploading to PyPI (production) ---"
python -m twine upload -u __token__ dist/*
echo "--- Successfully uploaded to PyPI! ---"
