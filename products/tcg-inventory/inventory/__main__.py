"""Command line entry point: `python -m inventory <command>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import (
    catalog, cli_intake, db, economics as ec, intake, ledger, pricing,
    selector, slots, tcgplayer_csv,
)


def _money(cents: int | None) -> str:
    return "—" if cents is None else f"${cents / 100:,.2f}"


def cmd_init(args: argparse.Namespace) -> int:
    conn = db.connect(with_catalog=False)
    was_new = not db.is_initialized(conn)
    db.initialize(conn)
    print(f"{'Created' if was_new else 'Updated'} {db.INVENTORY_DB}")

    try:
        db.attach_catalog(conn)
    except db.CatalogUnavailable as exc:
        print(f"\nCatalog not attached: {exc}", file=sys.stderr)
        return 1

    cards = conn.execute("SELECT COUNT(*) AS n FROM catalog.cards").fetchone()["n"]
    variants = conn.execute("SELECT COUNT(*) AS n FROM catalog.card_variants").fetchone()["n"]
    print(f"Catalog attached read-only: {cards:,} cards, {variants:,} variants")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    conn = db.connect(with_catalog=False)
    if not db.is_initialized(conn):
        print("Not initialized. Run: make init", file=sys.stderr)
        return 1

    counts = ledger.reconcile_counts(conn)
    total = sum(counts.values())
    print(f"Copies: {total}")
    for state, count in sorted(counts.items()):
        container = conn.execute(
            "SELECT container FROM copy_states WHERE state = ?", (state,)
        ).fetchone()
        where = f"  ({container['container']})" if container else ""
        print(f"  {state:<12} {count:>4}{where}")

    cap = slots.capacity(conn)
    print(f"\nBinder: {cap['occupied']}/{cap['total']} slots used, {cap['free']} free")

    print("\nChannel capacity:")
    for row in conn.execute("SELECT * FROM channel_usage ORDER BY channel"):
        count_cap = row["max_listing_count"]
        value_cap = row["max_listed_value_cents"]
        print(
            f"  {row['channel']:<10} "
            f"{row['live_listing_count']}/{count_cap if count_cap is not None else '-'} listings, "
            f"${row['live_listed_value_cents'] / 100:,.2f}"
            f"/{f'${value_cap / 100:,.0f}' if value_cap is not None else '-'} "
            f"({row['cap_period']})"
        )

    print("\nBreakeven (below this, listing isn't worth the handling):")
    for row in conn.execute("SELECT channel FROM channels WHERE is_enabled = 1"):
        chan = row["channel"]
        solo = ec.breakeven_price_cents(conn, chan)
        basket = ec.breakeven_price_cents(conn, chan, cards_in_order=8)
        print(f"  {chan:<10} ${solo / 100:>6.2f} solo   ${basket / 100:>6.2f} in an 8-card order")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    conn = db.connect()
    rows = catalog.search(conn, args.name, set_name=args.set, number=args.number)
    if not rows:
        print("No matches.")
        return 1

    for row in rows:
        price = row["current_price"] or 0.0
        print(
            f"[{row['variant_id']:>6}] {row['card_name']:<34.34} "
            f"{row['card_number']:<10.10} {row['sub_type']:<17.17} "
            f"${price:>9,.2f}  {row['set_name']:<28.28} {row['rarity'] or ''}"
        )

        health = catalog.price_health(conn, row["variant_id"])
        for warning in health.warnings:
            print(f"{'':>9}! {warning}")
    return 0


def cmd_intake(args: argparse.Namespace) -> int:
    conn = db.connect()
    taken_in = cli_intake.run(conn, acquisition_id=args.lot)
    print(f"Took in {taken_in} card(s).")

    if args.lot and taken_in:
        allocated = intake.allocate_lot_cost(conn, args.lot)
        print(f"Re-allocated lot {args.lot} across {len(allocated)} copies.")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    """Non-interactive intake, for scripting and for re-importing a CSV."""
    conn = db.connect()
    try:
        result = intake.add_copy(
            conn,
            args.variant,
            args.condition.upper(),
            acquisition_id=args.lot,
            cost_cents=round(args.cost * 100) if args.cost is not None else None,
            assign_slot=not args.no_slot,
        )
    except intake.NoCatalogEntry as exc:
        print(exc, file=sys.stderr)
        return 1

    where = f" → {result.slot}" if result.slot else " (collection, no slot)"
    print(
        f"copy {result.copy_id}: {result.card_name} ({result.sub_type}) "
        f"{result.condition_code} @ {_money(result.market_price_cents)}{where}"
    )
    return 0


def cmd_lot(args: argparse.Namespace) -> int:
    conn = db.connect()

    if args.lot_command == "new":
        lot_id = intake.create_acquisition(
            conn,
            args.date,
            round(args.cost * 100),
            source=args.source,
        )
        print(f"lot {lot_id}: {_money(round(args.cost * 100))} on {args.date}")
        return 0

    if args.lot_command == "allocate":
        allocated = intake.allocate_lot_cost(conn, args.lot_id)
        if not allocated:
            print("No copies attached to that lot yet.")
            return 1
        total = sum(allocated.values())
        print(f"Allocated {_money(total)} across {len(allocated)} copies:")
        for copy_id, cents in sorted(allocated.items(), key=lambda kv: -kv[1])[:10]:
            row = conn.execute(
                """
                SELECT c.variant_id, s.card_name, s.sub_type
                  FROM copies c JOIN catalog.screener_rows s ON s.variant_id = c.variant_id
                 WHERE c.copy_id = ?
                """,
                (copy_id,),
            ).fetchone()
            label = f"{row['card_name']} ({row['sub_type']})" if row else f"copy {copy_id}"
            print(f"  {_money(cents):>10}  {label}")
        if len(allocated) > 10:
            print(f"  … and {len(allocated) - 10} more")
        return 0

    for row in conn.execute("SELECT * FROM acquisitions ORDER BY acquired_on DESC"):
        attached = conn.execute(
            "SELECT COUNT(*) AS n FROM copies WHERE acquisition_id = ?",
            (row["acquisition_id"],),
        ).fetchone()["n"]
        print(
            f"lot {row['acquisition_id']:>3}  {row['acquired_on']}  "
            f"{_money(row['total_cost_cents']):>10}  {attached:>4} cards  "
            f"{row['source'] or ''}"
        )
    return 0


def cmd_shelf(args: argparse.Namespace) -> int:
    """What is physically in the binder, in slot order."""
    conn = db.connect()
    rows = conn.execute(
        """
        SELECT o.slot_number, o.copy_id, c.variant_id, c.condition_code, c.cost_cents,
               s.card_name, s.sub_type, s.set_name, s.current_price
          FROM slot_occupancy o
          JOIN copies c ON c.copy_id = o.copy_id
          LEFT JOIN catalog.screener_rows s ON s.variant_id = c.variant_id
         ORDER BY o.slot_number
        """
    ).fetchall()

    if not rows:
        print("Binder is empty.")
        return 0

    for row in rows:
        address = slots.address(conn, row["slot_number"])
        # Condition-adjusted, not the NM catalog price — this is what the card
        # would actually list at.
        price_cents = catalog.market_price_cents(
            conn, row["variant_id"], row["condition_code"]
        )
        live = intake.live_listings(conn, row["copy_id"])
        channels = ",".join(listing["channel"] for listing in live) or "unlisted"
        print(
            f"p{address.page:>2}/{address.pocket}  #{row['slot_number']:>3}  "
            f"copy {row['copy_id']:>4}  {row['card_name'] or '?':<30.30} "
            f"{row['sub_type'] or '':<16.16} {row['condition_code']:<4} "
            f"{_money(price_cents):>9}  {channels}"
        )

    capacity = slots.capacity(conn)
    print(f"\n{capacity['occupied']}/{capacity['total']} slots used")
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    """Pull a sold card. Prints where it is before freeing the slot."""
    conn = db.connect()
    address = slots.find_copy(conn, args.copy_id)
    if address is None:
        print(f"Copy {args.copy_id} is not in a binder.", file=sys.stderr)
        return 1

    print(f"Copy {args.copy_id} is in {address}")
    photos = conn.execute(
        "SELECT shot, original_path FROM photos WHERE copy_id = ? ORDER BY shot",
        (args.copy_id,),
    ).fetchall()
    if photos:
        print("Check it against intake photos before it goes in the mailer:")
        for photo in photos:
            print(f"  {photo['shot']:<8} {photo['original_path']}")

    intake.pull_copy(conn, args.copy_id)
    print(f"Slot {address.slot_number} freed.")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    """What to list where, given the caps."""
    conn = db.connect()
    channels = (
        [args.channel]
        if args.channel
        else [r["channel"] for r in conn.execute(
            "SELECT channel FROM channels WHERE is_enabled = 1 ORDER BY channel"
        )]
    )

    for channel in channels:
        plan = selector.build_plan(conn, channel)
        cap = f"/{plan.listing_cap}" if plan.listing_cap is not None else ""
        value_cap = (
            f"/{_money(plan.value_cap_cents)}" if plan.value_cap_cents is not None else ""
        )
        print(
            f"\n{channel.upper()} — list {plan.listing_count}{cap} cards, "
            f"{_money(plan.value_cents)}{value_cap}"
        )

        for candidate in plan.selected[: args.limit]:
            print(
                f"  copy {candidate.copy_id:>4}  "
                f"{candidate.card_name:<30.30} {candidate.sub_type:<15.15} "
                f"{candidate.condition_code:<4} {_money(candidate.price_cents):>9}  "
                f"velocity {candidate.velocity:.2f}"
            )
        if plan.listing_count > args.limit:
            print(f"  … and {plan.listing_count - args.limit} more")

        if plan.rejected:
            grouped: dict[str, int] = {}
            for rejection in plan.rejected:
                grouped[rejection.reason] = grouped.get(rejection.reason, 0) + 1
            print("  not listed:")
            for reason, count in sorted(grouped.items(), key=lambda kv: -kv[1]):
                print(f"    {count:>4}  {reason}")
    return 0


def cmd_reprice(args: argparse.Namespace) -> int:
    conn = db.connect()
    proposals = pricing.propose_all(conn, args.channel)
    if not proposals:
        print("Every live listing is priced where the rules want it.")
        return 0

    for proposal in proposals:
        arrow = "↑" if proposal.change_pct > 0 else "↓"
        flag = "auto" if proposal.is_auto_applicable else "REVIEW"
        print(
            f"  [{flag:>6}] {proposal.card_name:<28.28} {proposal.channel:<10} "
            f"{_money(proposal.current_cents):>9} {arrow} "
            f"{_money(proposal.proposed_cents):<9} "
            f"({proposal.change_pct:+.1f}%)  {proposal.reason}"
        )
        for blocker in proposal.blockers:
            print(f"{'':11}! {blocker}")

    if args.apply:
        applied, queued = pricing.apply_auto(conn, args.channel)
        print(f"\nApplied {applied}, left {queued} for review.")
    else:
        auto = sum(1 for p in proposals if p.is_auto_applicable and p.is_actionable)
        print(f"\n{auto} would auto-apply. Re-run with --apply to commit them.")
    return 0


def cmd_tcgplayer_csv(args: argparse.Namespace) -> int:
    """Round-trip a Seller Portal export with updated prices."""
    conn = db.connect()
    source = Path(args.template)
    try:
        rows, fieldnames = tcgplayer_csv.read_export(source)
    except (OSError, tcgplayer_csv.ColumnNotFound) as exc:
        print(f"Could not read {source}: {exc}", file=sys.stderr)
        return 1

    # Price every live TCGplayer listing we can match, keyed on (id, condition).
    condition_labels = {
        "NM": "Near Mint", "LP": "Lightly Played", "MP": "Moderately Played",
        "HP": "Heavily Played", "DMG": "Damaged",
    }
    prices: dict[tuple[str, str], int] = {}
    for row in conn.execute(
        """
        SELECT l.list_price_cents, c.product_id, c.condition_code, s.sub_type
          FROM listings l
          JOIN copies c ON c.copy_id = l.copy_id
          JOIN catalog.screener_rows s ON s.variant_id = c.variant_id
         WHERE l.channel = 'tcgplayer' AND l.ended_at IS NULL
        """
    ):
        label = condition_labels.get(row["condition_code"], row["condition_code"])
        if "Holofoil" in (row["sub_type"] or ""):
            label = f"{label} Foil"
        prices[(str(row["product_id"]), label)] = row["list_price_cents"]

    report = tcgplayer_csv.rewrite(rows, fieldnames, price_cents_by_key=prices)
    destination = Path(args.out)
    tcgplayer_csv.write_import(destination, rows, fieldnames)

    print(f"Read {report.row_count} rows from {source}")
    print(f"Priced {report.priced_count} of {len(prices)} live TCGplayer listings")
    print(f"Wrote {destination}")
    for warning in report.warnings:
        print(f"  ! {warning}")
    if report.priced_count < len(prices):
        print(
            "  ! Some listings had no matching row. Condition labels are the "
            "usual cause — check how your export spells them."
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inventory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create and seed the inventory database")
    sub.add_parser("status", help="counts, slot usage, channel capacity, breakevens")

    find = sub.add_parser("find", help="search the catalog for a card")
    find.add_argument("name")
    find.add_argument("--set", help="narrow by set name")
    find.add_argument("--number", help="narrow by collector number")

    take = sub.add_parser("intake", help="interactive batch intake")
    take.add_argument("--lot", type=int, help="attach these cards to an acquisition lot")

    add = sub.add_parser("add", help="take in one card non-interactively")
    add.add_argument("--variant", type=int, required=True)
    add.add_argument("--condition", default="NM")
    add.add_argument("--cost", type=float, help="in dollars")
    add.add_argument("--lot", type=int)
    add.add_argument("--no-slot", action="store_true", help="keeper, not for sale")

    lot = sub.add_parser("lot", help="acquisition lots and cost basis")
    lot_sub = lot.add_subparsers(dest="lot_command")
    lot_sub.add_parser("list")
    lot_new = lot_sub.add_parser("new")
    lot_new.add_argument("--cost", type=float, required=True, help="in dollars")
    lot_new.add_argument("--date", required=True, help="ISO date")
    lot_new.add_argument("--source")
    lot_alloc = lot_sub.add_parser("allocate", help="spread cost pro-rata by market value")
    lot_alloc.add_argument("lot_id", type=int)

    sub.add_parser("shelf", help="what is in the binder, in slot order")

    plan = sub.add_parser("plan", help="what to list where, given the caps")
    plan.add_argument("--channel", help="just this one")
    plan.add_argument("--limit", type=int, default=15, help="rows to show per channel")

    pull = sub.add_parser("pull", help="pull a sold card and free its slot")
    pull.add_argument("copy_id", type=int)

    reprice = sub.add_parser("reprice", help="what the pricing rules want to change")
    reprice.add_argument("--channel")
    reprice.add_argument("--apply", action="store_true", help="commit the auto-applicable moves")

    csv_cmd = sub.add_parser("tcgplayer-csv", help="fill a Seller Portal export with current prices")
    csv_cmd.add_argument("--template", required=True, help="CSV exported from the Pricing tab")
    csv_cmd.add_argument("--out", default="data/tcgplayer-import.csv")

    args = parser.parse_args(argv)
    handlers = {
        "init": cmd_init,
        "status": cmd_status,
        "find": cmd_find,
        "intake": cmd_intake,
        "add": cmd_add,
        "lot": cmd_lot,
        "shelf": cmd_shelf,
        "pull": cmd_pull,
        "plan": cmd_plan,
        "reprice": cmd_reprice,
        "tcgplayer-csv": cmd_tcgplayer_csv,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
