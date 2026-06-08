// Shared setup-only bundle pricing — the JS twin of Python `quote_services`
// (packages/schemas/offer.py). Integer cents in, integer cents out.
//
// This is the SINGLE JS pricing source: the Build-Your-Own-Bundle island uses it
// for the live cart, and the create-checkout Netlify function uses it to recompute
// the authoritative charge server-side. A cross-language golden test
// (tests/python/unit/test_agency_pricing_cross_language.py) pins it to Python so
// the two can never drift. Do not fork this math.

/**
 * Round a non-negative number to the nearest integer, half-up.
 * Matches Python's Decimal ROUND_HALF_UP for money (NOT banker's rounding).
 * Values of the form k+0.5 are exactly representable here (k*100+50)/100, so
 * the +0.5/floor trick rounds them up deterministically.
 * @param {number} value
 * @returns {number}
 */
export function roundHalfUp(value) {
  return Math.floor(value + 0.5);
}

/**
 * @typedef {{ min: number, max: number | null, pct: number }} DiscountTier
 * @typedef {{ setup_cents: number, monthly_cents: number }} ServiceLite
 * @typedef {{
 *   setupGrossCents: number, setupAfterCents: number, monthlyCents: number,
 *   savingsCents: number, tierPct: number, pricingMode: "tier" | "promo",
 * }} Quote
 */

/**
 * The setup discount % for a cart of `count` services (0 if no tier matches).
 * @param {number} count
 * @param {DiscountTier[]} tiers
 * @returns {number}
 */
export function tierPctFor(count, tiers) {
  for (const t of tiers) {
    if (count >= t.min && (t.max === null || t.max === undefined || count <= t.max)) {
      return t.pct;
    }
  }
  return 0;
}

/**
 * Price a set of services. With `setupPromoCents` (a preset's curated override)
 * the setup is pinned to that promo; otherwise the count-based tier discount
 * applies. Monthly is the plain component sum unless `monthlyPromoCents` pins it
 * (named packages only) — à-la-carte carts are never monthly-discounted.
 * @param {string[]} serviceIds
 * @param {Record<string, ServiceLite>} servicesById
 * @param {DiscountTier[]} tiers
 * @param {number | null} [setupPromoCents]
 * @param {number | null} [monthlyPromoCents]
 * @returns {Quote}
 */
export function quoteServices(
  serviceIds,
  servicesById,
  tiers,
  setupPromoCents = null,
  monthlyPromoCents = null,
) {
  let gross = 0;
  let monthly = 0;
  for (const id of serviceIds) {
    const s = servicesById[id];
    if (!s) throw new Error(`unknown service ${id}`);
    gross += s.setup_cents;
    monthly += s.monthly_cents;
  }

  let after;
  let tierPct = 0;
  let pricingMode;
  if (setupPromoCents !== null && setupPromoCents !== undefined) {
    after = setupPromoCents;
    pricingMode = "promo";
  } else {
    tierPct = tierPctFor(serviceIds.length, tiers);
    after = gross - roundHalfUp((gross * tierPct) / 100);
    pricingMode = "tier";
  }

  const monthlyAfter =
    monthlyPromoCents !== null && monthlyPromoCents !== undefined ? monthlyPromoCents : monthly;

  return {
    setupGrossCents: gross,
    setupAfterCents: after,
    monthlyCents: monthlyAfter,
    savingsCents: gross - after,
    tierPct,
    pricingMode,
  };
}

/**
 * Validate a selection's variant constraints — the JS twin of Python
 * ServiceCatalog.validate_selection. At most one service per `exclusive_group`,
 * and every `requires_group` satisfied. Returns an array of error strings (empty
 * = valid). The builder prevents invalid carts; the function calls this as the
 * authoritative server-side guard.
 * @param {string[]} serviceIds
 * @param {Record<string, any>} servicesById
 * @returns {string[]}
 */
export function validateSelection(serviceIds, servicesById) {
  const services = serviceIds.map((id) => servicesById[id]).filter(Boolean);
  const presentGroups = new Set(
    services.map((s) => s.exclusive_group).filter(Boolean),
  );
  const errors = [];
  const counts = {};
  for (const s of services) {
    if (s.exclusive_group) counts[s.exclusive_group] = (counts[s.exclusive_group] || 0) + 1;
  }
  for (const [group, n] of Object.entries(counts)) {
    if (n > 1) errors.push(`choose only one option for ${group} (got ${n})`);
  }
  for (const s of services) {
    if (s.requires_group && !presentGroups.has(s.requires_group)) {
      errors.push(`${s.name} requires a ${s.requires_group} option in the cart`);
    }
  }
  return errors;
}

/** Build an id→service map from the packages.json `services` array. */
export function servicesById(services) {
  /** @type {Record<string, ServiceLite>} */
  const map = {};
  for (const s of services) map[s.id] = s;
  return map;
}

/** Format integer cents as a whole-dollar string, e.g. 59900 → "$599". */
export function dollars(cents) {
  return `$${Math.round(cents / 100).toLocaleString("en-US")}`;
}
