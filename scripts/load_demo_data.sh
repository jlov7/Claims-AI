#!/usr/bin/env bash
set -e

# Demo Data Loader: Copies a sample PDF fixture into data/raw/demo as 20 demo claim documents
DEMO_DIR="data/raw/demo"
mkdir -p "$DEMO_DIR"

for i in $(seq -w 1 20); do
  cp tests/e2e/fixtures/sample.pdf "$DEMO_DIR/demo_claim_${i}.pdf"
done

echo "Copied 20 demo documents to $DEMO_DIR" 