#!/bin/bash
# Simple script to test the Human Action container locally

set -e  # Exit immediately if a command exits with non-zero status

echo "Building container..."
docker build -t human-action:test .

echo "Creating test directories..."
mkdir -p test-data/1-pdf
mkdir -p test-data/output

echo "Preparing test PDF..."
cp data/1-pdf/*.pdf test-data/1-pdf/ 2>/dev/null || echo "No PDF files found in data/1-pdf, using sample file"

# If no PDF exists, create a small test PDF
if [ -z "$(ls -A test-data/1-pdf/)" ]; then
    echo "Creating sample test PDF..."
    echo "Sample text" > test-data/1-pdf/sample.txt
    # If available, use text to pdf converter, otherwise just use the text file
    if command -v convert &> /dev/null; then
        convert test-data/1-pdf/sample.txt test-data/1-pdf/sample.pdf
        rm test-data/1-pdf/sample.txt
    else
        echo "ImageMagick not found, using text file as sample."
        mv test-data/1-pdf/sample.txt test-data/1-pdf/sample.pdf
    fi
fi

echo "Running unit tests in container..."
docker run --rm \
    -v "$(pwd)/test-data:/app/data" \
    human-action:test run_tests.py --unit

echo "Running a sample pipeline step..."
docker run --rm \
    -v "$(pwd)/test-data:/app/data" \
    human-action:test pipeline --help

echo "Test completed successfully!" 