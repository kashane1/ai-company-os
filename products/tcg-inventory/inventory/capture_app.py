"""Phone-as-camera capture server.

Run it on the Mac, open it on the phone over the same Wi-Fi. The phone shoots;
the photos land straight in the inventory database, already attached to the
right card.

The problem this solves is not moving bytes — AirDrop does that in ten seconds.
It is association: ninety photos in a folder, and no way to know which three
belong to the Charizard in slot 47. Here the card is chosen before the shutter,
so the link is structural and cannot drift.

Capture uses a plain file input with `capture="environment"`, which opens the
phone's own camera app and hands back the full-resolution, fully-processed
photo. No getUserMedia, no permissions dance, no custom capture UI, and the
image quality is whatever the phone normally produces rather than a webcam
frame.
"""

from __future__ import annotations

import socket

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from . import catalog, db, ebay_listing, photos

app = FastAPI(title="tcg-inventory capture")


def _conn():
    return db.connect()


def _lan_url(port: int) -> str:
    """The address to open on the phone."""
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        host = probe.getsockname()[0]
        probe.close()
    except OSError:
        host = socket.gethostname()
    return f"http://{host}:{port}"


_STYLE = """
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root { color-scheme: dark; }
  body { margin:0; padding:16px; background:#111; color:#eee;
         font:16px/1.45 -apple-system,BlinkMacSystemFont,system-ui,sans-serif; }
  h1 { font-size:19px; margin:0 0 4px; }
  .sub { color:#999; font-size:14px; margin-bottom:18px; }
  a { color:#6cf; text-decoration:none; }
  .card { display:block; padding:14px; margin-bottom:10px; background:#1c1c1e;
          border-radius:12px; border:1px solid #2c2c2e; }
  .card .name { font-weight:600; }
  .card .meta { color:#999; font-size:13px; margin-top:3px; }
  .pill { display:inline-block; padding:2px 8px; border-radius:99px;
          font-size:12px; background:#2c2c2e; color:#aaa; margin-left:6px; }
  .pill.done { background:#14532d; color:#86efac; }
  .shot { display:flex; align-items:center; gap:14px; padding:14px;
          margin-bottom:12px; background:#1c1c1e; border-radius:12px; }
  .shot img { width:64px; height:88px; object-fit:cover; border-radius:6px;
              background:#000; }
  .shot .label { flex:1; font-weight:600; text-transform:capitalize; }
  label.btn { display:inline-block; padding:12px 18px; background:#0a84ff;
              color:#fff; border-radius:10px; font-weight:600; cursor:pointer; }
  label.btn.retake { background:#2c2c2e; color:#ddd; }
  input[type=file] { display:none; }
  .title { background:#1c1c1e; border-radius:12px; padding:14px;
           margin-bottom:16px; font-size:13px; color:#bbb; }
  .title code { color:#eee; font-size:13px; word-break:break-word; }
</style>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    conn = _conn()
    pending = photos.queue(conn, limit=60)

    if not pending:
        body = (
            "<p>Nothing is waiting for photos.</p>"
            "<p class='sub'>Only cards above the eBay breakeven show up here — "
            "cheaper cards list on TCGplayer against a stock image.</p>"
        )
    else:
        rows = []
        for row in pending:
            have = len(photos.for_copy(conn, row["copy_id"]))
            pill = f"<span class='pill{' done' if have else ''}'>{have}/3</span>"
            price = catalog.market_price_cents(
                conn, row["variant_id"], row["condition_code"]
            )
            rows.append(
                f"<a class='card' href='/card/{row['copy_id']}'>"
                f"<div class='name'>{row['card_name']}{pill}</div>"
                f"<div class='meta'>{row['set_name']} · {row['sub_type']} · "
                f"{row['condition_code']} · ${(price or 0) / 100:,.2f}</div></a>"
            )
        body = "".join(rows)

    return (
        f"{_STYLE}<h1>Needs photos</h1>"
        f"<div class='sub'>{len(pending)} card(s) queued</div>{body}"
    )


@app.get("/card/{copy_id}", response_class=HTMLResponse)
def card_page(copy_id: int) -> HTMLResponse:
    conn = _conn()
    row = conn.execute(
        """
        SELECT c.copy_id, c.variant_id, c.condition_code, s.*
          FROM copies c
          JOIN catalog.screener_rows s ON s.variant_id = c.variant_id
         WHERE c.copy_id = ?
        """,
        (copy_id,),
    ).fetchone()
    if row is None:
        return HTMLResponse(f"{_STYLE}<p>No copy {copy_id}.</p>", status_code=404)

    have = photos.for_copy(conn, copy_id)
    title = ebay_listing.build_title(row, row["condition_code"])

    blocks = []
    for shot in photos.SHOTS:
        done = shot in have
        thumb = (
            f"<img src='/image/{copy_id}/{shot}' alt=''>"
            if done
            else "<img src='data:image/gif;base64,R0lGODlhAQABAAAAACw=' alt=''>"
        )
        blocks.append(
            f"<form class='shot' method='post' enctype='multipart/form-data' "
            f"action='/card/{copy_id}/{shot}'>"
            f"{thumb}<div class='label'>{shot}</div>"
            f"<label class='btn{' retake' if done else ''}'>"
            f"{'Retake' if done else 'Take'}"
            f"<input type='file' name='photo' accept='image/*' "
            f"capture='environment' onchange='this.form.submit()'></label></form>"
        )

    return HTMLResponse(
        f"{_STYLE}"
        f"<h1>{row['card_name']}</h1>"
        f"<div class='sub'>{row['set_name']} · {row['card_number']} · "
        f"{row['sub_type']} · {row['condition_code']}</div>"
        f"<div class='title'>eBay title ({title.length}/80)<br><code>{title.title}</code></div>"
        f"{''.join(blocks)}"
        f"<p style='margin-top:20px'><a href='/'>← back to the queue</a></p>"
    )


@app.post("/card/{copy_id}/{shot}")
async def upload(copy_id: int, shot: str, photo: UploadFile = File(...)):
    conn = _conn()
    data = await photo.read()
    suffix = "." + (photo.filename or "x.jpg").rsplit(".", 1)[-1].lower()

    try:
        photos.store(conn, copy_id, shot, data, original_suffix=suffix)
    except (ValueError, photos.UnreadableImage) as exc:
        return HTMLResponse(f"{_STYLE}<p>{exc}</p>", status_code=400)

    # Straight back to the card so the next shot is one tap away.
    return RedirectResponse(f"/card/{copy_id}", status_code=303)


@app.get("/image/{copy_id}/{shot}")
def image(copy_id: int, shot: str) -> Response:
    conn = _conn()
    row = photos.for_copy(conn, copy_id).get(shot)
    if row is None:
        return Response(status_code=404)
    path = row["listing_path"] or row["original_path"]
    try:
        return Response(open(path, "rb").read(), media_type="image/jpeg")
    except OSError:
        return Response(status_code=404)
