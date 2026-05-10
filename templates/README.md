# Template Development

Each bank template should be isolated behind the `StatementTemplate` interface.

## Add a Template

1. Create a module under `src/thai_bank_parser/templates/`.
2. Implement `StatementTemplate.parse(boxes, source_file)`.
3. Define fixed layout constants such as render scale and table crop.
4. Convert OCR boxes into the shared `StatementRow` schema.
5. Add the template to `src/thai_bank_parser/registry.py`.
6. Add tests with synthetic OCR boxes.

## Design Rules

- Do not change existing templates when adding a new bank.
- Keep `datetime_iso`, `direction`, `amount`, `withdrawal`, `deposit`, and
  `balance` consistent across banks.
- Use position when the PDF layout is positional. Do not rely only on OCR text
  labels when the visual layout carries the meaning.
- Validate with balance deltas whenever the statement provides balances.
- Keep private statement files outside the repo.

## Planned Template Keys

- `krungsri` - implemented
- `kbank` - planned
- `bangkok-bank` - planned
- `scb` - planned
