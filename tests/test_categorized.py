from thai_bank_parser.categorized import CATEGORIZED_COLUMNS, to_categorized_rows


def test_categorized_columns_match_sample_shape():
    assert CATEGORIZED_COLUMNS == [
        "tt number",
        "date",
        "time",
        "datetime",
        "datetime_iso",
        "transaction",
        "direction",
        "amount",
        "withdrawal",
        "deposit",
        "balance",
        "channel",
        "description",
        "Type",
        "Main_Category",
        "Sub_Category",
        "Sub2_Category",
        "Sub3_Category",
        "From",
        "To",
        "Column1",
        "Memo / Note",
        "Additional_Info",
        "Reference_No",
    ]


def test_categorized_export_formats_datetime_and_direction_sides():
    rows = to_categorized_rows(
        [
            {
                "date": "01/01/2026",
                "time": "09:08:07",
                "datetime": "01/01/2026 09:08:07",
                "datetime_iso": "2026-01-01 09:08:07",
                "transaction": "Transfer Deposit",
                "direction": "in",
                "amount": "1,000.00",
                "withdrawal": "",
                "deposit": "1,000.00",
                "balance": "5,000.00",
                "channel": "MOBILE",
                "description": "From Example Bank Acc No. : X000000",
            },
            {
                "date": "01/01/2026",
                "time": "10:09:08",
                "datetime": "01/01/2026 10:09:08",
                "datetime_iso": "2026-01-01 10:09:08",
                "transaction": "Spending",
                "direction": "out",
                "amount": "250.00",
                "withdrawal": "250.00",
                "deposit": "",
                "balance": "4,750.00",
                "channel": "POS",
                "description": "From Card No. 0000000000",
            },
        ],
        account_label="Self",
        additional_info="Converted by Thai Bank Parser",
    )

    assert rows[0]["tt number"] == "1"
    assert rows[0]["datetime"] == "01/01/2026 09:08"
    assert rows[0]["datetime_iso"] == "2026-01-01T09:08:00"
    assert rows[0]["amount"] == "1000"
    assert rows[0]["deposit"] == "1000"
    assert rows[0]["From"] == "Example Bank"
    assert rows[0]["To"] == "Self"
    assert rows[0]["Additional_Info"] == "Converted by Thai Bank Parser"
    assert rows[1]["withdrawal"] == "250"
    assert rows[1]["From"] == "Self"
    assert rows[1]["Main_Category"] == "Expense"
