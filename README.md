# Thai Bank Parser

Local-first OCR tooling for Thai bank statement PDFs.

The first implemented template is `krungsri`. The package is designed so new
fixed-layout bank templates can be added later for KBank, Bangkok Bank, SCB,
and other statement formats.

## Install

```powershell
python -m pip install .
```

For development:

```powershell
python -m pip install -e ".[dev]"
```

## CLI

List supported templates:

```powershell
thai-bank-parser templates
```

Convert a statement:

```powershell
thai-bank-parser convert --template krungsri --input "C:\Statements\krungsri.pdf" --output "C:\Statements\krungsri.csv"
```

Validate a generated CSV:

```powershell
thai-bank-parser validate --csv "C:\Statements\krungsri.csv"
```

Convert the normalized parser CSV into the categorized sheet format:

```powershell
thai-bank-parser categorize --input "C:\Statements\krungsri.csv" --output "C:\Statements\krungsri_categorized.csv"
```

Useful conversion options:

```powershell
thai-bank-parser convert `
  --template krungsri `
  --input "C:\Statements\krungsri.pdf" `
  --output "C:\Statements\krungsri.csv" `
  --work-dir "C:\Statements\.parser-work" `
  --force-ocr `
  --debug-json "C:\Statements\.parser-work\ocr-debug.json"
```

## Output Schema

Every template should write the same CSV columns:

| Column | Meaning |
| --- | --- |
| `bank` | Bank name, for example `Krungsri`. |
| `template` | Template key, for example `krungsri`. |
| `source_file` | Input file name only, not full local path. |
| `page` | Statement page number. |
| `date` | Original date as `DD/MM/YYYY`. |
| `time` | Transaction time as `HH:MM:SS`. |
| `datetime` | Combined display datetime. |
| `datetime_iso` | Merge-safe `YYYY-MM-DD HH:MM:SS`. |
| `transaction` | OCR transaction label. |
| `direction` | `in` for deposit, `out` for withdrawal. |
| `amount` | Normalized transaction amount. |
| `withdrawal` | Amount when money leaves. |
| `deposit` | Amount when money enters. |
| `balance` | Outstanding balance after transaction. |
| `channel` | Channel from the statement, if present. |
| `description` | Description field from the statement. |
| `ocr_confidence` | Lowest relevant OCR confidence for the row. |
| `amount_source` | `ocr` or `balance_delta`. |

## Categorized Sheet Export

The `categorize` command converts the normalized CSV into the wider categorized
sheet schema:

```text
tt number,date,time,datetime,datetime_iso,transaction,direction,amount,withdrawal,deposit,balance,channel,description,Type,Main_Category,Sub_Category,Sub2_Category,Sub3_Category,From,To,Column1,Memo / Note,Additional_Info,Reference_No
```

This export is intentionally separate from `convert`, so the clean normalized
parser output remains unchanged. Categories are rule-based starting values that
can be reviewed or edited later.

## Krungsri Template

Krungsri statements use one combined `Withdrawal/Deposit` header, but the
amount position determines direction:

- left side of the amount band = withdrawal / out
- right side of the amount band = deposit / in

The template uses fixed OCR coordinates for the static table layout and then
checks balance deltas as a hard validation pass.

## Future AI Instructions

When asking an AI agent to use or extend this package:

1. Never commit real bank statements, generated CSVs, OCR JSON, rendered pages,
   or debug images.
2. Use real private PDFs only in local ignored work directories.
3. Run `thai-bank-parser validate` after conversion.
4. Prefer adding a new bank as a new template module instead of changing the
   Krungsri parser.
5. Keep the output schema stable across all bank templates.

## Development

Run tests:

```powershell
pytest
```

Run a privacy check before publishing:

```powershell
git status --short
git ls-files
```

Then search for private strings relevant to your local test data before pushing.
The repository intentionally ignores PDFs, CSVs, images, OCR caches, logs, and
debug artifacts.
