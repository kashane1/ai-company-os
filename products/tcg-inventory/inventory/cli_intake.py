"""Interactive intake: catalogue a card, grade it, slot it, price it.

Built for a batch session rather than a single card. You work through a stack
of 25-30 in one sitting, so every prompt has a default you can accept with
Enter, and the condition and lot carry over between cards until changed.
"""

from __future__ import annotations

import sqlite3

from . import catalog, economics as ec, intake

CONDITIONS = ("NM", "LP", "MP", "HP", "DMG")


def _prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{label}{suffix}: ").strip()
    except EOFError:
        raise KeyboardInterrupt from None
    return answer or (default or "")


def _money(cents: int | None) -> str:
    return "—" if cents is None else f"${cents / 100:,.2f}"


def _choose_variant(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    """Search, then disambiguate. The finish is where identification goes wrong.

    The same card name routinely spans a $0.30 Normal and a $47 Special
    Illustration Rare, so candidates are always shown with finish and price
    even when there is only a handful.
    """
    rows = catalog.search(conn, name, limit=12)
    if not rows:
        print("  no matches")
        return None

    for index, row in enumerate(rows, start=1):
        price = row["current_price"] or 0.0
        print(
            f"  {index:>2}. {row['card_name']:<32.32} {row['card_number']:<9.9} "
            f"{row['sub_type']:<17.17} ${price:>9,.2f}  {row['set_name']:<26.26}"
        )

    choice = _prompt("  pick #", "1")
    if not choice.isdigit() or not 1 <= int(choice) <= len(rows):
        print("  skipped")
        return None
    return rows[int(choice) - 1]


def _show_verdict(conn: sqlite3.Connection, price_cents: int | None) -> None:
    if not price_cents:
        print("     no market price — set one by hand before listing")
        return

    for verdict in ec.evaluate_channels(conn, price_cents, cards_in_order={"tcgplayer": 6}):
        if verdict.is_viable:
            net = verdict.proceeds.net_after_labor_cents
            print(f"     {verdict.channel:<10} list — nets {_money(net)} after labor")
        else:
            print(f"     {verdict.channel:<10} skip — {verdict.blocked_reason}")


def run(conn: sqlite3.Connection, acquisition_id: int | None = None) -> int:
    """Loop until the user stops. Returns how many copies were taken in."""
    print("Intake. Enter a card name, or blank to finish.\n")

    condition = "NM"
    taken_in = 0

    while True:
        try:
            name = _prompt("card")
        except KeyboardInterrupt:
            print()
            break
        if not name:
            break

        card = _choose_variant(conn, name)
        if card is None:
            print()
            continue

        condition = (_prompt("  condition", condition) or "NM").upper()
        if condition not in CONDITIONS:
            print(f"  unknown condition, using NM (one of {', '.join(CONDITIONS)})")
            condition = "NM"

        cost_raw = _prompt("  cost, blank if from a lot", "")
        cost_cents = round(float(cost_raw) * 100) if cost_raw else None

        health = catalog.price_health(conn, card["variant_id"])
        result = intake.add_copy(
            conn,
            card["variant_id"],
            condition,
            acquisition_id=acquisition_id,
            cost_cents=cost_cents,
        )
        taken_in += 1

        print(
            f"  → copy {result.copy_id}: {result.card_name} ({result.sub_type}) "
            f"{result.condition_code} @ {_money(result.market_price_cents)}"
        )
        print(f"     put it in {result.slot}")
        for warning in health.warnings:
            print(f"     ! {warning}")
        _show_verdict(conn, result.market_price_cents)
        print()

    return taken_in
