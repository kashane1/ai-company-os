"""Tests for the TCGplayer Seller Portal CSV round-trip.

The format is unverified, so the property that matters most is that a column
this tool does not understand survives untouched.
"""

from __future__ import annotations

import pytest
from inventory import tcgplayer_csv as tsv

EXPORT = """TCGplayer Id,Product Line,Set Name,Product Name,Number,Condition,\
TCG Market Price,Total Quantity,Add to Quantity,TCG Marketplace Price,\
Some Future Column
32055,Pokemon,Paldea Evolved,Iono,269/193,Near Mint Foil,47.05,1,0,45.00,keep-me
32040,Pokemon,Paldea Evolved,Iono,254/193,Lightly Played Foil,10.28,2,0,9.50,also-keep
25961,Pokemon,Evolving Skies,Umbreon VMAX,095/203,Near Mint Foil,29.49,1,0,28.00,and-me
"""


@pytest.fixture
def export_file(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text(EXPORT, encoding="utf-8")
    return path


def test_read_preserves_the_header_verbatim(export_file):
    rows, fieldnames = tsv.read_export(export_file)

    assert len(rows) == 3
    assert fieldnames[0] == "TCGplayer Id"
    assert "Some Future Column" in fieldnames


def test_rewrite_updates_only_the_matching_rows(export_file):
    rows, fieldnames = tsv.read_export(export_file)

    report = tsv.rewrite(
        rows, fieldnames,
        price_cents_by_key={("32055", "Near Mint Foil"): 4999},
    )

    assert report.priced_count == 1
    assert rows[0]["TCG Marketplace Price"] == "49.99"
    assert rows[1]["TCG Marketplace Price"] == "9.50"  # untouched
    assert rows[2]["TCG Marketplace Price"] == "28.00"


def test_columns_this_tool_does_not_know_about_survive(export_file):
    """The whole reason for round-tripping instead of generating a header."""
    rows, fieldnames = tsv.read_export(export_file)

    tsv.rewrite(rows, fieldnames, price_cents_by_key={("32055", "Near Mint Foil"): 100})

    assert rows[0]["Some Future Column"] == "keep-me"
    assert rows[0]["TCG Market Price"] == "47.05"


def test_round_trip_preserves_column_order(export_file, tmp_path):
    rows, fieldnames = tsv.read_export(export_file)
    out = tmp_path / "import.csv"

    tsv.write_import(out, rows, fieldnames)

    assert out.read_text().splitlines()[0] == EXPORT.splitlines()[0]


def test_condition_is_part_of_the_key(export_file):
    """Same product, different condition, is a different SKU and price."""
    rows, fieldnames = tsv.read_export(export_file)

    tsv.rewrite(
        rows, fieldnames,
        price_cents_by_key={
            ("32055", "Near Mint Foil"): 5000,
            ("32040", "Lightly Played Foil"): 800,
        },
    )

    assert rows[0]["TCG Marketplace Price"] == "50.00"
    assert rows[1]["TCG Marketplace Price"] == "8.00"


def test_price_floor_is_enforced(export_file):
    """TCGplayer rejects anything under a cent."""
    rows, fieldnames = tsv.read_export(export_file)

    tsv.rewrite(rows, fieldnames, price_cents_by_key={("32055", "Near Mint Foil"): 0})

    assert rows[0]["TCG Marketplace Price"] == "0.01"


def test_quantity_delta_is_written(export_file):
    rows, fieldnames = tsv.read_export(export_file)

    report = tsv.rewrite(
        rows, fieldnames, quantity_delta_by_key={("32055", "Near Mint Foil"): -1}
    )

    assert report.quantity_changed_count == 1
    assert rows[0]["Add to Quantity"] == "-1"


def test_column_matching_ignores_case_and_spacing(tmp_path):
    path = tmp_path / "odd.csv"
    path.write_text("tcgplayer id,condition,marketplace price\n999,Near Mint,1.00\n")
    rows, fieldnames = tsv.read_export(path)

    report = tsv.rewrite(rows, fieldnames, price_cents_by_key={("999", "Near Mint"): 250})

    assert report.priced_count == 1
    assert rows[0]["marketplace price"] == "2.50"


def test_missing_id_column_raises_rather_than_guessing(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("Name,Price\nIono,1.00\n")
    rows, fieldnames = tsv.read_export(path)

    with pytest.raises(tsv.ColumnNotFound):
        tsv.rewrite(rows, fieldnames, price_cents_by_key={("1", ""): 100})


def test_missing_price_column_raises(tmp_path):
    path = tmp_path / "noprice.csv"
    path.write_text("TCGplayer Id,Condition\n1,Near Mint\n")
    rows, fieldnames = tsv.read_export(path)

    with pytest.raises(tsv.ColumnNotFound):
        tsv.rewrite(rows, fieldnames, price_cents_by_key={("1", "Near Mint"): 100})


def test_missing_quantity_column_warns_instead_of_failing(tmp_path):
    """Quantity semantics are the least verified part of the format."""
    path = tmp_path / "noqty.csv"
    path.write_text("TCGplayer Id,Condition,TCG Marketplace Price\n1,Near Mint,1.00\n")
    rows, fieldnames = tsv.read_export(path)

    report = tsv.rewrite(rows, fieldnames, quantity_delta_by_key={("1", "Near Mint"): -1})

    assert report.quantity_changed_count == 0
    assert any("Add to Quantity" in w for w in report.warnings)
