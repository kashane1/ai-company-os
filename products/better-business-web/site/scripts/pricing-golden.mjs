// Golden-vector runner for the cross-language pricing drift guard.
//
// Reads {carts, services, tiers} as JSON on stdin, prices each cart with the
// shared JS helper, and writes the resulting cents to stdout as JSON. The Python
// test (tests/python/unit/test_agency_pricing_cross_language.py) feeds the SAME
// inputs to Python `quote_services` and asserts byte-identical integers, so the
// JS and Python money math can never drift.
//
// Inputs are passed explicitly (not read from packages.json) so the test can also
// exercise synthetic half-cent fixtures the real catalog doesn't contain.

import { quoteServices } from "../src/lib/pricing.mjs";

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

const { carts, services, tiers } = JSON.parse(await readStdin());
const byId = {};
for (const [id, s] of Object.entries(services)) byId[id] = s;

const out = carts.map((cart) =>
  quoteServices(cart.service_ids, byId, tiers, cart.setup_promo_cents ?? null),
);
process.stdout.write(JSON.stringify(out));
