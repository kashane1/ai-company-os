/** @jsxImportSource react */
import { useMemo, useReducer, useState } from "react";
import {
  dollars,
  quoteServices,
  servicesById as toServicesMap,
  tierPctFor,
} from "../lib/pricing.mjs";

type Service = {
  id: string;
  name: string;
  tier: string;
  bill_type: "one_time" | "recurring";
  setup_cents: number;
  monthly_cents: number;
  blurb: string;
  self_serve: boolean;
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

type Action =
  | { type: "toggle"; id: string }
  | { type: "preset"; ids: string[] }
  | { type: "clear" };

function reducer(state: Set<string>, action: Action): Set<string> {
  switch (action.type) {
    case "toggle": {
      const next = new Set(state);
      next.has(action.id) ? next.delete(action.id) : next.add(action.id);
      return next;
    }
    case "preset":
      return new Set(action.ids);
    case "clear":
      return new Set();
  }
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
  const byId = useMemo(() => toServicesMap(services), [services]);
  const grouped = useMemo(() => {
    const map: Record<string, Service[]> = {};
    for (const s of buyable) (map[s.tier] ??= []).push(s);
    return map;
  }, [buyable]);

  const [selected, dispatch] = useReducer(reducer, new Set<string>());
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

        {TIER_ORDER.filter((t) => grouped[t]?.length).map((tier) => (
          <fieldset className="byo-group" key={tier}>
            <legend>{TIER_LABELS[tier] ?? tier}</legend>
            <div className="byo-cards">
              {grouped[tier].map((s) => {
                const on = selected.has(s.id);
                return (
                  <label className="byo-card" key={s.id} data-selected={on}>
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => dispatch({ type: "toggle", id: s.id })}
                    />
                    <span className="byo-card-head">
                      <span className="byo-card-name">{s.name}</span>
                      <span className="byo-check" aria-hidden="true">✓</span>
                    </span>
                    <span className="byo-card-blurb">{s.blurb}</span>
                    <span className="byo-card-price">
                      {s.setup_cents > 0 && <>{dollars(s.setup_cents)} setup</>}
                      {s.setup_cents > 0 && s.monthly_cents > 0 && " · "}
                      {s.monthly_cents > 0 && <>{dollars(s.monthly_cents)}/mo</>}
                    </span>
                  </label>
                );
              })}
            </div>
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
