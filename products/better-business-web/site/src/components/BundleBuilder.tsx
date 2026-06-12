/** @jsxImportSource react */
import { useEffect, useMemo, useReducer, useState } from "react";
import { dollars, quoteServices, tierPctFor } from "../lib/pricing.mjs";

type Service = {
  id: string;
  name: string;
  tier: string;
  bill_type: "one_time" | "recurring";
  setup_cents: number;
  monthly_cents: number;
  blurb: string;
  self_serve: boolean;
  exclusive_group: string;
  requires_group: string;
};

type Bundle = {
  id: string;
  name: string;
  description: string;
  setup_after_cents: number;
  monthly_cents: number;
  service_ids: string[];
};

type Tier = { min: number; max: number | null; pct: number };

type Props = {
  services: Service[];
  bundles: Bundle[];
  discountTiers: Tier[];
  checkoutEndpoint?: string;
};

const TIER_LABELS: Record<string, string> = {
  tier_1: "Foundations",
  tier_2: "Get found & booked",
  tier_3: "Grow & convert",
};

const TIER_ORDER = ["tier_1", "tier_2", "tier_3"];

/** Conversion Lab à-la-carte services — shown in their own group on /build. */
const CONVERSION_LAB_IDS = ["conversion_snapshot", "conversion_audit", "ad_copy_lab"] as const;

type Action =
  | { type: "set"; ids: Set<string> }
  | { type: "preset"; ids: string[] }
  | { type: "clear" };

function reducer(_state: Set<string>, action: Action): Set<string> {
  switch (action.type) {
    case "set":
      return action.ids;
    case "preset":
      return new Set(action.ids);
    case "clear":
      return new Set();
  }
}

// Toggle a service while enforcing variant rules: selecting a service in an
// exclusive group swaps out its siblings; deselecting a base removes any
// modifiers that depended on that group.
function nextSelection(
  selected: Set<string>,
  id: string,
  byId: Record<string, Service>,
): Set<string> {
  const svc = byId[id];
  const next = new Set(selected);
  if (next.has(id)) {
    next.delete(id);
  } else {
    if (svc?.exclusive_group) {
      for (const other of [...next]) {
        if (byId[other]?.exclusive_group === svc.exclusive_group) next.delete(other);
      }
    }
    next.add(id);
  }
  const groups = new Set(
    [...next].map((x) => byId[x]?.exclusive_group).filter(Boolean),
  );
  for (const x of [...next]) {
    const req = byId[x]?.requires_group;
    if (req && !groups.has(req)) next.delete(x);
  }
  return next;
}

function sameSet(a: Set<string>, ids: string[]): boolean {
  return a.size === ids.length && ids.every((id) => a.has(id));
}

export default function BundleBuilder({
  services,
  bundles,
  discountTiers,
  checkoutEndpoint = "/.netlify/functions/create-checkout",
}: Props) {
  const buyable = useMemo(() => services.filter((s) => s.self_serve), [services]);
  const byId = useMemo(
    () => Object.fromEntries(services.map((s) => [s.id, s])) as Record<string, Service>,
    [services],
  );
  const conversionLab = useMemo(
    () =>
      CONVERSION_LAB_IDS.map((id) => byId[id]).filter(
        (s): s is Service => Boolean(s?.self_serve),
      ),
    [byId],
  );
  const grouped = useMemo(() => {
    const lab = new Set<string>(CONVERSION_LAB_IDS);
    const map: Record<string, Service[]> = {};
    for (const s of buyable) {
      if (lab.has(s.id)) continue;
      (map[s.tier] ??= []).push(s);
    }
    return map;
  }, [buyable]);

  const [selected, dispatch] = useReducer(reducer, new Set<string>());

  // Preselect a package when arriving from a landing-page CTA (/build?preset=…).
  useEffect(() => {
    const presetId = new URLSearchParams(window.location.search).get("preset");
    const b = presetId ? bundles.find((x) => x.id === presetId) : null;
    if (b) dispatch({ type: "preset", ids: b.service_ids });
  }, [bundles]);

  const [business, setBusiness] = useState("");
  const [contact, setContact] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const ids = useMemo(() => [...selected], [selected]);

  // A preset matches only when the selection is exactly its service set.
  const matchedPreset = useMemo(
    () => bundles.find((b) => sameSet(selected, b.service_ids)) ?? null,
    [bundles, selected],
  );

  const quote = useMemo(
    () =>
      quoteServices(
        ids,
        byId,
        discountTiers,
        matchedPreset ? matchedPreset.setup_after_cents : null,
      ),
    [ids, byId, discountTiers, matchedPreset],
  );

  // "Add N more to unlock the next tier" nudge (custom carts only).
  const nextTier = useMemo(() => {
    if (matchedPreset) return null;
    const current = tierPctFor(ids.length, discountTiers);
    const upgrade = discountTiers.find((t) => t.pct > current);
    if (!upgrade || ids.length >= upgrade.min) return null;
    return { need: upgrade.min - ids.length, pct: upgrade.pct };
  }, [matchedPreset, ids.length, discountTiers]);

  const dueToday = quote.setupAfterCents + quote.monthlyCents; // setup + first month
  const canBuy = ids.length > 0 && business.trim() && contact.trim();

  async function buy() {
    if (!canBuy || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(checkoutEndpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          service_ids: ids,
          preset_id: matchedPreset?.id ?? null,
          business: business.trim(),
          contact: contact.trim(),
          nonce: crypto.randomUUID(),
          bot_field: "", // honeypot
        }),
      });
      if (!res.ok) throw new Error(`checkout failed (${res.status})`);
      const data = await res.json();
      if (!data?.url) throw new Error("no checkout url returned");
      window.location.href = data.url;
    } catch (e) {
      setError("Sorry — couldn't start checkout. Please try again.");
      setSubmitting(false);
    }
  }

  function renderServiceCard(s: Service) {
    const on = selected.has(s.id);
    const baseInCart =
      !s.requires_group ||
      [...selected].some((x) => byId[x]?.exclusive_group === s.requires_group);
    const locked = !on && !baseInCart;
    return (
      <label className="byo-card" key={s.id} data-selected={on} data-locked={locked}>
        <input
          type="checkbox"
          checked={on}
          disabled={locked}
          onChange={() => dispatch({ type: "set", ids: nextSelection(selected, s.id, byId) })}
        />
        <span className="byo-card-head">
          <span className="byo-card-name">{s.name}</span>
          <span className="byo-check" aria-hidden="true">
            ✓
          </span>
        </span>
        <span className="byo-card-blurb">{s.blurb}</span>
        <span className="byo-card-price">
          {s.exclusive_group && <span className="byo-pickone">pick one · </span>}
          {locked && <span className="byo-pickone">needs a booking option · </span>}
          {s.setup_cents > 0 && <>{dollars(s.setup_cents)} setup</>}
          {s.setup_cents > 0 && s.monthly_cents > 0 && " · "}
          {s.monthly_cents > 0 && <>{dollars(s.monthly_cents)}/mo</>}
        </span>
      </label>
    );
  }

  return (
    <div className="byo">
      <div className="byo-main">
        <div className="byo-presets" role="group" aria-label="Start from a package">
          {bundles.map((b, i) => {
            const active = sameSet(selected, b.service_ids);
            return (
              <button
                key={b.id}
                type="button"
                className="byo-preset"
                aria-pressed={active}
                data-active={active}
                onClick={() => dispatch({ type: "preset", ids: b.service_ids })}
              >
                <span className="byo-preset-name">{b.name}</span>
                <span className="byo-preset-price">
                  {dollars(b.setup_after_cents)} setup · {dollars(b.monthly_cents)}/mo
                </span>
                <span className="byo-preset-badge">
                  {i === bundles.length - 1 ? "Most popular" : "Best value"} — cheaper than building it yourself
                </span>
              </button>
            );
          })}
        </div>

        {conversionLab.length > 0 && (
          <fieldset className="byo-group">
            <legend>Conversion Lab</legend>
            <p className="byo-group-note">
              Pressure-test your page or ad copy before spend or a rebuild — add one
              à-la-carte or pair with Package C.
            </p>
            <div className="byo-cards">{conversionLab.map(renderServiceCard)}</div>
          </fieldset>
        )}

        {TIER_ORDER.filter((t) => grouped[t]?.length).map((tier) => (
          <fieldset className="byo-group" key={tier}>
            <legend>{TIER_LABELS[tier] ?? tier}</legend>
            <div className="byo-cards">{grouped[tier].map(renderServiceCard)}</div>
          </fieldset>
        ))}
      </div>

      <aside className="byo-cart" aria-label="Your bundle">
        <h2 className="byo-cart-title">
          {matchedPreset ? matchedPreset.name : ids.length ? "Custom bundle" : "Your bundle"}
        </h2>

        <div className="byo-cart-totals" aria-live="polite" aria-atomic="true">
          {ids.length === 0 ? (
            <p className="byo-empty">Select a service to get started.</p>
          ) : (
            <>
              <div className="byo-due">
                <span className="byo-due-label">Due today</span>
                <span className="byo-due-amount">{dollars(dueToday)}</span>
              </div>
              <ul className="byo-lines">
                <li>
                  <span>Setup (one-time)</span>
                  <span>
                    {quote.savingsCents > 0 && (
                      <s className="byo-strike">{dollars(quote.setupGrossCents)}</s>
                    )}{" "}
                    {dollars(quote.setupAfterCents)}
                  </span>
                </li>
                {quote.savingsCents > 0 && (
                  <li className="byo-discount">
                    <span>
                      Bundle discount
                      {quote.pricingMode === "tier" && ` (${quote.tierPct}% off setup)`}
                    </span>
                    <span>−{dollars(quote.savingsCents)}</span>
                  </li>
                )}
                <li>
                  <span>First month</span>
                  <span>{dollars(quote.monthlyCents)}</span>
                </li>
              </ul>
              <div className="byo-then">
                then <strong>{dollars(quote.monthlyCents)}/mo</strong>, billed monthly · cancel anytime
              </div>
              {nextTier && (
                <p className="byo-nudge">
                  Add {nextTier.need} more service{nextTier.need > 1 ? "s" : ""} to unlock{" "}
                  {nextTier.pct}% off setup.
                </p>
              )}
            </>
          )}
        </div>

        {ids.length > 0 && (
          <div className="byo-checkout">
            <label className="byo-field">
              <span>Business name</span>
              <input
                type="text"
                value={business}
                autoComplete="organization"
                onChange={(e) => setBusiness(e.target.value)}
                placeholder="Joe's Plumbing"
              />
            </label>
            <label className="byo-field">
              <span>Email or phone</span>
              <input
                type="text"
                value={contact}
                autoComplete="email"
                onChange={(e) => setContact(e.target.value)}
                placeholder="you@business.com"
              />
            </label>
            {/* honeypot — must stay empty */}
            <input
              type="text"
              name="bot_field"
              tabIndex={-1}
              autoComplete="off"
              aria-hidden="true"
              style={{ position: "absolute", left: "-9999px", width: 1, height: 1 }}
              onChange={() => {}}
            />
            <button
              type="button"
              className="byo-buy"
              disabled={!canBuy || submitting}
              onClick={buy}
            >
              {submitting ? "Starting…" : `Start — ${dollars(dueToday)} today`}
            </button>
            {error && <p className="byo-error">{error}</p>}
            <ol className="byo-next">
              <li>Pay today (secure checkout by Stripe)</li>
              <li>A real person emails you within 1 business day to kick off</li>
              <li>Your site & setup get underway that week</li>
            </ol>
          </div>
        )}
      </aside>
    </div>
  );
}
