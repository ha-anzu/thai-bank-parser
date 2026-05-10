# Privacy Rules

This repository is intended to be public. Treat bank data as private by default.

## Never Commit

- Real bank statement PDFs
- Generated CSV exports from real statements
- OCR JSON, OCR text dumps, rendered page images, screenshots, and logs
- Account holder names
- Account numbers or masked account fragments from real statements
- Real transaction descriptions, balances, or amounts copied from private data
- Absolute local paths from private machines

## Allowed

- Parser source code
- Tests using synthetic values only
- Documentation with fake paths and fake sample data
- Template coordinate logic

## Local Debugging

It is fine to use real bank PDFs locally while developing. Keep all generated
work under ignored folders such as `work/`, `debug/`, `cache/`, `ocr/`,
`rendered/`, or `output/`.

Before publishing, inspect staged files and search for private strings that
appear in your local data.
