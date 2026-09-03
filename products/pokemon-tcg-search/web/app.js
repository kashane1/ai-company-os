/* TCG Highs and Lows front end.
 *
 * No framework and no build step: the app is one screener request rendered
 * into a table, so a small amount of explicit DOM code is easier to follow
 * than a toolchain. All user-supplied and API-supplied text goes in via
 * textContent, never innerHTML.
 */

'use strict';

const PAGE_SIZE = 50;

// The sort lives here rather than on the select, because there are two controls
// for it — the select's named shortlist and the column headings — and neither can
// express everything the other can. One piece of state, two views of it.
const DEFAULT_SORT = 'discount';
const DEFAULT_IS_DESCENDING = true;

const state = {
  offset: 0,
  total: 0,
  benchmark: '52w',
  sort: DEFAULT_SORT,
  isDescending: DEFAULT_IS_DESCENDING,
  requestToken: 0,   // guards against out-of-order responses overwriting newer ones
};

const el = (id) => document.getElementById(id);

const form = el('filter-form');
const tableBody = el('results-body');

/* ------------------------------------------------------------ formatting */

const money = (value) => {
  if (value === null || value === undefined) return '—';
  const digits = value >= 100 ? 0 : 2;
  return `$${value.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
};

const percent = (value, digits = 1) =>
  value === null || value === undefined ? '—' : `${value.toFixed(digits)}%`;

const signedPercent = (value) => {
  if (value === null || value === undefined) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
};

const changeClass = (value) => {
  if (value === null || value === undefined) return 'change--flat';
  if (value > 0.5) return 'change--up';
  if (value < -0.5) return 'change--down';
  return 'change--flat';
};

const dayCount = (days) => {
  if (days === null || days === undefined) return '—';
  if (days < 60) return `${days}d`;
  const months = Math.round(days / 30.44);
  return months < 24 ? `${months}mo` : `${(days / 365.25).toFixed(1)}y`;
};

/* --------------------------------------------------------- query building */

/** Read the filter form into URL parameters the API understands. */
function buildParams() {
  const data = new FormData(form);
  const params = new URLSearchParams();

  const put = (key, value) => {
    if (value !== null && value !== undefined && value !== '') params.append(key, value);
  };

  put('benchmark', data.get('benchmark'));
  put('min_discount_pct', data.get('min_discount_pct'));
  put('max_discount_pct', data.get('max_discount_pct'));
  // Sent unconditionally: blank must mean "no floor", not "fall back to the
  // API's $1 default", or clearing the box would look like it did nothing.
  params.append('min_price', data.get('min_price') || 0);
  put('max_price', data.get('max_price'));
  put('search', (data.get('search') || '').trim());
  put('min_range_position_pct', data.get('min_range_position_pct'));
  put('max_range_position_pct', data.get('max_range_position_pct'));
  put('min_release_year', data.get('min_release_year'));
  put('max_release_year', data.get('max_release_year'));
  put('min_history_days', data.get('min_history_days'));
  put('min_observations_30d', data.get('min_observations_30d'));
  put('max_spread_pct', data.get('max_spread_pct'));
  put('min_distinct_prices_90d', data.get('min_distinct_prices_90d'));

  // The momentum select is sugar over the two change bounds; keeping the
  // translation here means the API keeps a single, explicit filter vocabulary.
  const momentum = data.get('momentum');
  if (momentum === 'stabilised') put('min_change_7d_pct', 0);
  if (momentum === 'falling') put('max_change_7d_pct', -0.0001);
  if (momentum === 'capitulating') put('max_change_7d_pct', -5);

  params.append('exclude_price_outliers', data.get('exclude_price_outliers') ? 'true' : 'false');
  params.append('exclude_release_spikes', data.get('exclude_release_spikes') ? 'true' : 'false');
  params.append('exclude_truncated_peaks', data.get('exclude_truncated_peaks') ? 'true' : 'false');

  // One checklist drives either filter; its own mode select decides which.
  // Sending the same values as both include and exclude would return nothing,
  // so it is deliberately one or the other.
  const putChecklist = (name, modeField) => {
    const key = data.get(modeField) === 'exclude' ? `exclude_${name}` : name;
    for (const value of data.getAll(name)) params.append(key, value);
  };

  putChecklist('group_ids', 'set_mode');
  putChecklist('rarities', 'rarity_mode');
  putChecklist('sub_types', 'sub_type_mode');
  putChecklist('card_classes', 'card_class_mode');
  for (const kind of data.getAll('trainer_kinds')) params.append('trainer_kinds', kind);

  params.append('sort', state.sort);
  params.append('descending', state.isDescending ? 'true' : 'false');

  params.append('limit', PAGE_SIZE);
  params.append('offset', state.offset);
  return params;
}

/* ------------------------------------------------------- shareable filters */

/* A shared link describes the *form*, not the API request: it carries control
 * names and values as typed, so reopening it is the same as sitting down at the
 * rail and setting each control by hand. Translating to API vocabulary stays in
 * buildParams, which then runs over the restored form exactly as it always does.
 *
 * Only controls that differ from their authored default travel. That keeps a
 * link short enough to paste into a message, and means a default we revise later
 * is not frozen into every link ever copied.
 */

// The sort belongs to the results bar rather than the filter form, so it is
// collected separately. Its name is its own to avoid colliding with the `sort`
// the API takes, which is only half of this value.
const SORT_KEY = 'sort';

/* ------------------------------------------------------------------- sorting */

const sortButtons = [...document.querySelectorAll('.grid__sort')];

/** The `key:direction` spelling used by the select and by shared links. */
function sortValue(sort = state.sort, isDescending = state.isDescending) {
  return `${sort}:${isDescending ? 'desc' : 'asc'}`;
}

/** Adopt a `key:direction` string. Unknown keys are ignored rather than sent to
 *  the API, which rejects them: an edited or stale link should lose its sort, not
 *  the whole page. Returns whether anything was adopted. */
function applySortValue(value) {
  const [sort, direction] = String(value).split(':');
  const isKnown =
    sortButtons.some((button) => button.dataset.sort === sort) ||
    [...el('sort').options].some((option) => option.value.split(':')[0] === sort);
  if (!isKnown || !sort) return false;

  state.sort = sort;
  state.isDescending = direction !== 'asc';
  syncSortViews();
  return true;
}

/** Point both the headings and the select at the current sort. */
function syncSortViews() {
  const active = sortButtons.find((button) => button.dataset.sort === state.sort);

  for (const button of sortButtons) {
    const th = button.closest('th');
    const isActive = button === active;
    button.classList.toggle('grid__sort--active', isActive);
    button.classList.toggle('grid__sort--desc', isActive && state.isDescending);
    th.setAttribute('aria-sort', isActive ? (state.isDescending ? 'descending' : 'ascending') : 'none');
    // The heading text alone reads as a column name, not as a control, so the
    // hint spells out what a click will do rather than what it currently is.
    // "Ascending" rather than "low to high", because one of these columns sorts
    // names and A–Z is not a low.
    const label = button.querySelector('.grid__sort-label').textContent;
    button.title = isActive
      ? `Sorted by ${label}, ${state.isDescending ? 'descending' : 'ascending'}. Click to reverse.`
      : `Sort by ${label}, ascending.`;
  }

  const select = el('sort');
  const wanted = sortValue();
  const custom = el('sort-custom');
  // The custom option is excluded from the lookup: it carries whatever value it
  // was last relabelled for, so leaving it in makes it match itself, and it would
  // then be hidden as if it were a real preset and never be renamed again.
  const preset = [...select.options].find(
    (option) => option !== custom && option.value === wanted,
  );
  if (preset) {
    select.value = wanted;
    custom.hidden = true;
    // Blanked so a later sync cannot match a stale value.
    custom.value = '';
  } else {
    // No shortlist name for this one, so the select borrows the column's own
    // wording. Named after the heading, it still tracks a benchmark rename. The
    // arrow matches the one in the grid rather than spelling out a direction that
    // would have to read differently for names than for numbers.
    custom.hidden = false;
    custom.value = wanted;
    custom.textContent = active
      ? `${active.querySelector('.grid__sort-label').textContent} ${state.isDescending ? '↓' : '↑'}`
      : wanted;
    select.value = wanted;
  }
}

/** The value a control returns to on Reset. The DOM tracks this for us. */
function authoredValue(field) {
  if (field.tagName !== 'SELECT') return field.defaultValue;
  const preset = [...field.options].find((option) => option.defaultSelected);
  return (preset || field.options[0] || { value: '' }).value;
}

/** Every named, enabled control in the filter form, in document order. */
function* filterFields() {
  for (const field of form.elements) {
    if (field.name && !field.disabled) yield field;
  }
}

/** The current filter state, as the query string of a shareable link. */
function filterState() {
  const params = new URLSearchParams();
  // Checkboxes are compared as a group: one name covers a whole checklist, and
  // "which boxes are ticked" is the unit that has a default, not each box.
  const groups = new Map();

  for (const field of filterFields()) {
    if (field.type === 'checkbox') {
      const group = groups.get(field.name) || { ticked: [], authored: [] };
      if (field.checked) group.ticked.push(field.value);
      if (field.defaultChecked) group.authored.push(field.value);
      groups.set(field.name, group);
    } else if (field.type === 'radio') {
      // A radio's value is fixed; what varies is which one is checked. Comparing
      // value against the authored value — the test every other control uses —
      // would be comparing it against itself, and the group would never travel.
      if (field.checked && !field.defaultChecked) params.append(field.name, field.value);
    } else if (field.value !== authoredValue(field)) {
      params.append(field.name, field.value);
    }
  }

  for (const [name, group] of groups) {
    if (group.ticked.join(' ') === group.authored.join(' ')) continue;
    // An empty value says "this group is deliberately all-off". Leaving the key
    // out would mean "untouched", which is a different thing for the switches
    // that ship ticked.
    if (group.ticked.length === 0) params.append(name, '');
    for (const value of group.ticked) params.append(name, value);
  }

  if (state.sort !== DEFAULT_SORT || state.isDescending !== DEFAULT_IS_DESCENDING) {
    params.append(SORT_KEY, sortValue());
  }
  return params;
}

/** Put a shared link's state back on the controls. Names the link does not
 *  mention keep their default, which is what makes a partial link work. */
function applyFilterState(params) {
  const wanted = new Map();  // checkbox name -> the values that link ticks

  for (const field of filterFields()) {
    if (!params.has(field.name)) continue;
    if (field.type === 'checkbox') {
      if (!wanted.has(field.name)) wanted.set(field.name, new Set(params.getAll(field.name)));
      field.checked = wanted.get(field.name).has(field.value);
    } else if (field.type === 'radio') {
      // Assigning to .value would rewrite what this radio stands for. The link
      // picks one of the group, so tick the match and leave the rest alone.
      field.checked = field.value === params.get(field.name);
    } else if (field.tagName !== 'SELECT') {
      field.value = params.get(field.name);
    } else if ([...field.options].some((option) => option.value === params.get(field.name))) {
      // A select silently blanks itself when handed a value it has no option
      // for, so an edited or stale link would clear the control rather than
      // leave it alone. Ignoring the unknown value keeps the default.
      field.value = params.get(field.name);
    }
  }

  if (params.has(SORT_KEY)) applySortValue(params.get(SORT_KEY));

  syncRangeOutputs();
  updateBenchmarkHint();
}

/** The read-outs beside the sliders are rendered by JS, so they need telling
 *  whenever a slider moves without a user having dragged it. */
function syncRangeOutputs() {
  el('discount-output').textContent = el('min-discount').value;
  el('history-output').textContent = el('min-history').value;
  el('liquidity-output').textContent = el('min-observations').value;
  el('movement-output').textContent = el('min-movement').value;
}

/* -------------------------------------------------------------- rendering */

function rangeCell(row) {
  const cell = document.createElement('td');
  cell.className = 'range';
  if (row.pct_of_52w_range === null || row.pct_of_52w_range === undefined) {
    cell.textContent = '—';
    return cell;
  }

  const position = Math.max(0, Math.min(100, row.pct_of_52w_range));
  const track = document.createElement('div');
  track.className = 'range__track';
  const marker = document.createElement('div');
  marker.className = 'range__marker';
  marker.style.left = `${position}%`;
  track.appendChild(marker);

  const value = document.createElement('div');
  value.className = 'range__value';
  value.textContent = `${money(row.low_52w)} – ${money(row.high_52w)}`;

  cell.append(track, value);
  cell.title = `${position.toFixed(0)}% up from the 52-week low`;
  return cell;
}

function cardCell(row) {
  const cell = document.createElement('td');
  const wrap = document.createElement('div');
  wrap.className = 'card-cell';

  if (row.image_url) {
    const image = document.createElement('img');
    image.className = 'card-cell__thumb';
    image.src = row.image_url;
    image.alt = '';
    image.loading = 'lazy';
    wrap.appendChild(image);
  }

  const text = document.createElement('div');
  const name = document.createElement('div');
  name.className = 'card-cell__name';
  name.textContent = row.card_name;

  if (row.sub_type && row.sub_type !== 'Normal') {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.textContent = row.sub_type === 'Reverse Holofoil' ? 'Reverse' : row.sub_type;
    name.appendChild(tag);
  }
  // The set's release year, as a tag rather than in the meta line: era is one of
  // the first things you read a card by, and the meta line is already a long run
  // of dot-separated text. Its own colour keeps it from reading as a variant
  // label (blue) or a data-quality warning (amber).
  const releaseYear = (row.released_on || '').slice(0, 4);
  if (releaseYear) {
    const tag = document.createElement('span');
    tag.className = 'tag tag--year';
    tag.textContent = releaseYear;
    tag.title = `Set released ${row.released_on}.`;
    name.appendChild(tag);
  }
  if (row.peak_is_first_observation) {
    const tag = document.createElement('span');
    tag.className = 'tag tag--warn';
    tag.textContent = 'peak at data edge';
    tag.title = 'The peak is our oldest datapoint, so the true peak may be higher.';
    name.appendChild(tag);
  }
  if (row.distinct_prices_90d !== undefined && row.distinct_prices_90d <= 3) {
    const tag = document.createElement('span');
    tag.className = 'tag tag--warn';
    tag.textContent = 'thin';
    tag.title =
      `Only ${row.distinct_prices_90d} distinct price(s) in 90 days — an illiquid ` +
      'market, so the price is closer to a stale quote than a live one.';
    name.appendChild(tag);
  }

  const meta = document.createElement('div');
  meta.className = 'card-cell__meta';
  // Only non-Pokemon are labelled: "Pokemon" on four rows in five is noise, and
  // its absence reads as the default rather than as missing data.
  const typeLabel =
    row.card_class && row.card_class !== 'Pokemon'
      ? row.trainer_kind || row.card_class
      : null;
  meta.textContent = [row.set_name, row.card_number, row.rarity, typeLabel]
    .filter(Boolean)
    .join(' · ');

  text.append(name, meta);
  wrap.appendChild(text);
  cell.appendChild(wrap);
  return cell;
}

function numericCell(text, className) {
  const cell = document.createElement('td');
  cell.className = className ? `numeric ${className}` : 'numeric';
  cell.textContent = text;
  return cell;
}

function renderRows(rows, { append }) {
  // A preview left over from the old results would be pinned to a row that no
  // longer exists, and would name a card the new filters just excluded.
  if (!append) {
    hidePeek();
    tableBody.replaceChildren();
  }

  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const tr = document.createElement('tr');
    tr.tabIndex = 0;
    tr.append(
      cardCell(row),
      numericCell(money(row.current_price)),
      numericCell(money(row.reference_price)),
      numericCell(percent(row.discount_pct), 'discount'),
      rangeCell(row),
      numericCell(signedPercent(row.change_7d_pct), changeClass(row.change_7d_pct)),
      numericCell(signedPercent(row.change_30d_pct), changeClass(row.change_30d_pct)),
      numericCell(dayCount(row.days_since_peak)),
    );

    const open = () => {
      hidePeek();  // the dialog carries its own artwork; two would fight
      showDetail(row.variant_id);
    };
    tr.addEventListener('click', open);
    tr.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open();
      }
    });
    fragment.appendChild(tr);
  }
  tableBody.appendChild(fragment);
}

/* ------------------------------------------------------------- the search */

async function runSearch({ append = false } = {}) {
  if (!append) state.offset = 0;

  const token = ++state.requestToken;
  const params = buildParams();
  el('result-count').textContent = append ? 'Loading more…' : 'Searching…';

  let payload;
  try {
    const response = await fetch(`/api/screener?${params}`);
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    payload = await response.json();
  } catch (error) {
    if (token !== state.requestToken) return;
    showNotice(`Could not load results: ${error.message}`);
    el('result-count').textContent = 'Request failed.';
    return;
  }

  // A slower earlier request must not clobber a newer render.
  if (token !== state.requestToken) return;

  // This request worked, so whatever the last one complained about is history.
  hideNotice();

  state.total = payload.total;
  state.benchmark = payload.benchmark;
  el('reference-heading').textContent = payload.benchmark_label;
  // That heading just took a new name, which the sort tooltips and the select's
  // borrowed label both quote.
  syncSortViews();

  renderRows(payload.results, { append });

  const shown = tableBody.children.length;
  el('result-count').innerHTML = '';
  const count = document.createElement('span');
  count.textContent = `${payload.total.toLocaleString()} cards below their ${payload.benchmark_label}`;
  const shownNote = document.createElement('span');
  shownNote.textContent = payload.total ? ` — showing ${shown.toLocaleString()}` : '';
  el('result-count').append(count, shownNote);

  el('empty').hidden = payload.total > 0;
  el('load-more').hidden = shown >= payload.total;
}

function loadMore() {
  state.offset += PAGE_SIZE;
  runSearch({ append: true });
}

/* ------------------------------------------------------------ card detail */

function priceChart(history, peakPrice) {
  const width = 660;
  const height = 200;
  const pad = { top: 12, right: 46, bottom: 20, left: 8 };

  const points = history.filter((point) => typeof point.market_price === 'number');
  if (points.length < 2) return null;

  const prices = points.map((point) => point.market_price);
  const maxPrice = Math.max(...prices, peakPrice || 0);
  const minPrice = Math.min(...prices);
  const span = maxPrice - minPrice || maxPrice || 1;

  const firstDay = Date.parse(points[0].date);
  const lastDay = Date.parse(points[points.length - 1].date);
  const dayeSpan = lastDay - firstDay || 1;

  const x = (date) =>
    pad.left + ((Date.parse(date) - firstDay) / dayeSpan) * (width - pad.left - pad.right);
  const y = (price) =>
    pad.top + (1 - (price - minPrice) / span) * (height - pad.top - pad.bottom);

  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('class', 'chart');
  svg.setAttribute('role', 'img');
  svg.setAttribute(
    'aria-label',
    `Price history from ${points[0].date} to ${points[points.length - 1].date}`,
  );

  const defs = document.createElementNS(svgNS, 'defs');
  defs.innerHTML =
    '<linearGradient id="chart-fade" x1="0" y1="0" x2="0" y2="1">' +
    '<stop offset="0%" stop-color="#6ea8ff" stop-opacity="0.28"/>' +
    '<stop offset="100%" stop-color="#6ea8ff" stop-opacity="0"/></linearGradient>';
  svg.appendChild(defs);

  // Horizontal gridlines with price labels on the right.
  for (const fraction of [0, 0.5, 1]) {
    const price = minPrice + span * fraction;
    const lineY = y(price);
    const line = document.createElementNS(svgNS, 'line');
    line.setAttribute('class', 'chart__grid');
    line.setAttribute('x1', pad.left);
    line.setAttribute('x2', width - pad.right);
    line.setAttribute('y1', lineY);
    line.setAttribute('y2', lineY);
    svg.appendChild(line);

    const label = document.createElementNS(svgNS, 'text');
    label.setAttribute('class', 'chart__axis');
    label.setAttribute('x', width - pad.right + 6);
    label.setAttribute('y', lineY + 3);
    label.textContent = money(price);
    svg.appendChild(label);
  }

  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(p.date).toFixed(1)} ${y(p.market_price).toFixed(1)}`).join(' ');

  const area = document.createElementNS(svgNS, 'path');
  area.setAttribute('class', 'chart__area');
  area.setAttribute(
    'd',
    `${path} L${x(points[points.length - 1].date).toFixed(1)} ${height - pad.bottom} ` +
      `L${x(points[0].date).toFixed(1)} ${height - pad.bottom} Z`,
  );
  svg.appendChild(area);

  const line = document.createElementNS(svgNS, 'path');
  line.setAttribute('class', 'chart__line');
  line.setAttribute('d', path);
  svg.appendChild(line);

  if (peakPrice && peakPrice <= maxPrice) {
    const peakLine = document.createElementNS(svgNS, 'line');
    peakLine.setAttribute('class', 'chart__peak');
    peakLine.setAttribute('x1', pad.left);
    peakLine.setAttribute('x2', width - pad.right);
    peakLine.setAttribute('y1', y(peakPrice));
    peakLine.setAttribute('y2', y(peakPrice));
    svg.appendChild(peakLine);
  }

  for (const [index, anchor] of [[0, 'start'], [points.length - 1, 'end']]) {
    const label = document.createElementNS(svgNS, 'text');
    label.setAttribute('class', 'chart__axis');
    label.setAttribute('x', x(points[index].date));
    label.setAttribute('y', height - 6);
    label.setAttribute('text-anchor', anchor);
    label.textContent = points[index].date;
    svg.appendChild(label);
  }

  return svg;
}

function statList(pairs) {
  const list = document.createElement('dl');
  list.className = 'detail__stats';
  for (const [label, value, title] of pairs) {
    // Each pair needs its own wrapper: bare dt/dd siblings would each occupy a
    // separate grid cell, collapsing the grid into a tall two-column list.
    const cell = document.createElement('div');
    const dt = document.createElement('dt');
    dt.textContent = label;
    const dd = document.createElement('dd');
    dd.textContent = value;
    if (title) cell.title = title;
    cell.append(dt, dd);
    list.appendChild(cell);
  }
  return list;
}

async function showDetail(variantId) {
  const dialog = el('detail');
  const body = el('detail-body');
  body.replaceChildren();
  dialog.showModal();

  let card;
  try {
    const response = await fetch(`/api/variants/${variantId}`);
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    card = await response.json();
  } catch (error) {
    const message = document.createElement('p');
    message.className = 'detail__note';
    message.textContent = `Could not load this card: ${error.message}`;
    body.appendChild(message);
    return;
  }

  const head = document.createElement('div');
  head.className = 'detail__head';

  if (card.image_url) {
    const image = document.createElement('img');
    image.className = 'detail__image';
    image.src = card.image_url;
    image.alt = card.card_name;
    head.appendChild(image);
  }

  const headText = document.createElement('div');
  headText.className = 'detail__headtext';
  const title = document.createElement('h2');
  title.className = 'detail__title';
  title.textContent = card.card_name;
  const sub = document.createElement('p');
  sub.className = 'detail__sub';
  sub.textContent = [card.set_name, card.card_number, card.rarity, card.sub_type]
    .filter(Boolean)
    .join(' · ');

  headText.append(
    title,
    sub,
    statList([
      ['Current', money(card.current_price), `As of ${card.as_of_date}`],
      ['52w high', money(card.high_52w), `${percent(card.discount_from_52w_high_pct)} below`],
      ['6mo high', money(card.high_26w), `${percent(card.discount_from_26w_high_pct)} below`],
      ['Recorded peak', money(card.peak_price), `Set on ${card.peak_date}`],
      ['Off 52w high', percent(card.discount_from_52w_high_pct)],
      ['Off peak', percent(card.discount_from_peak_pct)],
      ['7 day', signedPercent(card.change_7d_pct)],
      ['30 day', signedPercent(card.change_30d_pct)],
      ['90 day', signedPercent(card.change_90d_pct)],
      ['52w range pos.', percent(card.pct_of_52w_range, 0)],
      [
        'Listing spread',
        percent(card.spread_pct, 0),
        'Gap between the cheapest and dearest listing, over the market price. ' +
          'It spans every condition on offer, so values in the hundreds of ' +
          'percent are normal — treat it as a rough width, not a bid-ask.',
      ],
      ['Priced days /30', String(card.observation_count_30d)],
      [
        'Price moves /90d',
        String(card.distinct_prices_90d ?? '—'),
        'Distinct market prices in the last 90 days. Low means an illiquid, ' +
          'stale quote rather than a stable market.',
      ],
    ]),
  );
  head.appendChild(headText);
  body.appendChild(head);

  const chartWrap = document.createElement('div');
  chartWrap.className = 'detail__chart';
  const chartTitle = document.createElement('h3');
  chartTitle.textContent = 'Market price history';
  chartWrap.appendChild(chartTitle);

  const chart = priceChart(card.history || [], card.peak_price);
  if (chart) {
    chartWrap.appendChild(chart);
  } else {
    const note = document.createElement('p');
    note.className = 'detail__note';
    note.textContent = 'Not enough history to chart.';
    chartWrap.appendChild(note);
  }
  body.appendChild(chartWrap);

  if (card.tcgplayer_url) {
    const actions = document.createElement('div');
    actions.className = 'detail__actions';
    const link = document.createElement('a');
    link.className = 'button';
    link.href = card.tcgplayer_url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'View listings on TCGplayer →';
    actions.appendChild(link);
    body.appendChild(actions);
  }

  const note = document.createElement('p');
  note.className = 'detail__note';
  note.textContent =
    'TCGplayer market price for Near Mint, ungraded, English. The dashed line marks ' +
    'the recorded peak. Not a guaranteed buy price, and not investment advice.';
  body.appendChild(note);
}

/* -------------------------------------------------------- card hover peek */

const HOVER_INTENT_MS = 110;  // long enough to ignore a pointer sweeping past
const PEEK_GAP = 14;          // clearance between the thumbnail and the preview
const PEEK_EDGE = 12;         // smallest gap the preview keeps from the viewport
const PEEK_ARROW_INSET = 20;  // keeps the caret clear of the rounded corners
const PEEK_MAX_HEIGHT = 430;
const CARD_ASPECT = 0.716;    // a Pokemon card is 63mm x 88mm

// Rows are rebuilt on every search, so the preview is one persistent element
// driven by delegated events rather than a node per row. It anchors to the
// thumbnail instead of the cursor: a preview that tracks the mouse jitters
// while it is being read, one pinned to the row stays still.
const peek = {
  root: el('card-peek'),
  image: el('card-peek-img'),
  row: null,
  timer: 0,
  token: 0,  // invalidates a slow hi-res load once the pointer has moved on
};

const canHover = window.matchMedia('(hover: hover)');

/** The CDN serves each product at several widths; rows use the 200px one. */
const largeImageUrl = (url) => url.replace(/_200w\.jpg$/, '_in_1000x1000.jpg');

/** Origin, on one axis, that makes `scale(scale)` sit the preview box exactly on
 *  the thumbnail. A transform fixes its origin point, not the box centre, so
 *  anchoring on the thumbnail's centre is only right when the two centres already
 *  agree — true vertically, but never horizontally, since the preview is offset
 *  to one side. Solves centre + (boxCentre - centre) * scale = thumbCentre. */
const zoomOrigin = (boxCentre, thumbCentre, scale) =>
  (thumbCentre - boxCentre * scale) / (1 - scale);

function showPeek(row) {
  const thumb = row.querySelector('.card-cell__thumb');
  if (!thumb) {
    hidePeek();
    return;
  }

  const token = ++peek.token;
  const thumbBox = thumb.getBoundingClientRect();

  const height = Math.min(PEEK_MAX_HEIGHT, window.innerHeight - PEEK_EDGE * 2);
  const width = height * CARD_ASPECT;

  // To the left of the thumbnail: that keeps the preview off the numbers, which
  // are the point of the table, and over the filter rail, which is not being
  // read mid-hover. The rail leaves slightly less than the full gap, so the
  // preview squeezes up to the screen edge before the right side is considered.
  let left = Math.max(PEEK_EDGE, thumbBox.left - PEEK_GAP - width);
  if (left + width > thumbBox.left) {
    left = Math.max(
      PEEK_EDGE,
      Math.min(thumbBox.right + PEEK_GAP, window.innerWidth - PEEK_EDGE - width),
    );
  }
  const top = Math.min(
    window.innerHeight - PEEK_EDGE - height,
    Math.max(PEEK_EDGE, thumbBox.top + thumbBox.height / 2 - height / 2),
  );

  const thumbCentreX = thumbBox.left + thumbBox.width / 2;
  const thumbCentreY = thumbBox.top + thumbBox.height / 2;

  const scale = thumbBox.width / width;
  const originX = zoomOrigin(left + width / 2, thumbCentreX, scale);
  const originY = zoomOrigin(top + height / 2, thumbCentreY, scale);

  Object.assign(peek.root.style, {
    left: `${Math.round(left)}px`,
    top: `${Math.round(top)}px`,
    width: `${Math.round(width)}px`,
    height: `${Math.round(height)}px`,
    transformOrigin: `${(originX - left).toFixed(1)}px ${(originY - top).toFixed(1)}px`,
  });
  peek.root.style.setProperty('--peek-from', scale.toFixed(4));

  // The caret sits level with the thumbnail, which is the preview's own centre
  // until the viewport clamps the box; kept off the rounded corners either way.
  const pointsLeft = left > thumbCentreX;
  peek.root.classList.toggle('card-peek--points-left', pointsLeft);
  peek.root.classList.toggle('card-peek--points-right', !pointsLeft);
  peek.root.style.setProperty(
    '--peek-arrow-y',
    `${Math.min(height - PEEK_ARROW_INSET, Math.max(PEEK_ARROW_INSET, thumbCentreY - top)).toFixed(1)}px`,
  );

  // The row thumbnail is already decoded, so it paints on this frame; the sharp
  // copy takes over when it arrives rather than opening on an empty box.
  const small = thumb.currentSrc || thumb.src;
  const large = largeImageUrl(small);
  peek.image.src = small;
  if (large !== small) {
    const sharp = new Image();
    sharp.addEventListener('load', () => {
      if (peek.token === token) peek.image.src = large;
    });
    sharp.src = large;
  }

  peek.root.hidden = false;
  peek.root.classList.remove('card-peek--in');
  void peek.root.offsetWidth;  // commit the collapsed state before animating out of it
  peek.root.classList.add('card-peek--in');
  peek.row = row;
}

function hidePeek() {
  clearTimeout(peek.timer);
  peek.token += 1;
  peek.row = null;
  // Only the class comes off: `hidden` would cut the collapse animation short.
  peek.root.classList.remove('card-peek--in');
}

function queuePeek(row) {
  if (row === peek.row) return;
  clearTimeout(peek.timer);
  // Once a preview is up the user has committed to browsing the art, so moving
  // between rows switches straight away instead of making them wait again.
  const delay = peek.root.classList.contains('card-peek--in') ? 0 : HOVER_INTENT_MS;
  peek.timer = setTimeout(() => showPeek(row), delay);
}

if (canHover.matches) {
  tableBody.addEventListener('mouseover', (event) => {
    const row = event.target.closest('tr');
    if (row) queuePeek(row);
  });
  tableBody.addEventListener('mouseleave', hidePeek);
  // Capture: the results table and the filter rail scroll independently, and a
  // preview pinned to a row that has moved is worse than no preview.
  window.addEventListener('scroll', hidePeek, { passive: true, capture: true });
}

// Keyboard users arrow through the same rows, so focus gets the same preview.
tableBody.addEventListener('focusin', (event) => {
  const row = event.target.closest('tr');
  if (row) showPeek(row);
});
tableBody.addEventListener('focusout', hidePeek);

/* ---------------------------------------------------------------- filters */

function renderChecklist(container, items, { name, valueKey, labelKey }) {
  container.replaceChildren();
  for (const item of items) {
    const label = document.createElement('label');
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.name = name;
    input.value = item[valueKey];

    const text = document.createElement('span');
    text.className = 'checklist__name';
    text.textContent = item[labelKey];

    const count = document.createElement('span');
    count.className = 'checklist__count';
    count.textContent = item.variant_count.toLocaleString();

    label.append(input, text, count);
    label.dataset.searchText = String(item[labelKey]).toLowerCase();
    container.appendChild(label);
  }
}

async function loadFilters() {
  const response = await fetch('/api/filters');
  if (!response.ok) return;
  const options = await response.json();

  renderChecklist(el('set-list'), options.sets, {
    name: 'group_ids',
    valueKey: 'group_id',
    labelKey: 'name',
  });
  renderChecklist(el('rarity-list'), options.rarities, {
    name: 'rarities',
    valueKey: 'rarity',
    labelKey: 'rarity',
  });
  renderChecklist(el('subtype-list'), options.sub_types, {
    name: 'sub_types',
    valueKey: 'sub_type',
    labelKey: 'sub_type',
  });
  renderChecklist(el('card-class-list'), options.card_classes, {
    name: 'card_classes',
    valueKey: 'card_class',
    labelKey: 'card_class',
  });
  renderChecklist(el('trainer-kind-list'), options.trainer_kinds, {
    name: 'trainer_kinds',
    valueKey: 'trainer_kind',
    labelKey: 'trainer_kind',
  });

  // Say out loud how many Trainers the feed never assigned a kind, so a narrowed
  // trainer search does not look like it lost cards for no reason.
  const trainerTotal = (options.card_classes.find((c) => c.card_class === 'Trainer') || {})
    .variant_count;
  const kindTotal = options.trainer_kinds.reduce((sum, k) => sum + k.variant_count, 0);
  const unkinded = (trainerTotal || 0) - kindTotal;
  el('trainer-kind-hint').textContent = unkinded > 0
    ? `Narrows within Trainers. ${unkinded.toLocaleString()} Trainers carry no kind in the feed and are left out when you pick one.`
    : 'Narrows within Trainers.';

  // Bound the year inputs to the years we actually hold, and say what they are.
  const years = options.release_years || {};
  if (years.min && years.max) {
    for (const id of ['min-release-year', 'max-release-year']) {
      const input = el(id);
      input.min = years.min;
      input.max = years.max;
    }
    el('min-release-year').placeholder = years.min;
    el('max-release-year').placeholder = years.max;
    el('release-year-hint').textContent =
      `The year the card's set was released. Data covers ${years.min}–${years.max}.`;
  }
}

async function loadMeta() {
  const response = await fetch('/api/meta');
  if (!response.ok) return;
  const meta = await response.json();

  const format = {
    screener_rows: (value) => value.toLocaleString(),
    observation_count: (value) => value.toLocaleString(),
  };
  for (const node of document.querySelectorAll('[data-coverage]')) {
    const key = node.dataset.coverage;
    const value = meta[key];
    node.textContent = value === null || value === undefined
      ? '—'
      : (format[key] ? format[key](value) : value);
  }

  const caveats = el('caveats');
  caveats.replaceChildren();
  for (const text of meta.caveats || []) {
    const item = document.createElement('li');
    item.textContent = text;
    caveats.appendChild(item);
  }
  el('price-basis').textContent = `${meta.price_basis} · source: ${meta.source}`;

  // The recorded peak is only trustworthy relative to how much history exists,
  // so the caveat is shown only when that benchmark is actually selected.
  state.historyStart = meta.history_start;
  updateBenchmarkHint();
}

function updateBenchmarkHint() {
  const hint = el('benchmark-hint');
  const isPeak = el('benchmark').value === 'peak';
  hint.classList.toggle('field__hint--warn', isPeak);
  hint.textContent = isPeak
    ? `Our history starts ${state.historyStart || '2024-02-08'}, so this is the peak ` +
      'since then — not a true all-time high. Cards that peaked earlier will look ' +
      'less discounted than they are.'
    : 'This window sits entirely inside our price history, so the high is exact.';
}

/* A notice is a transient report, not a piece of the page: it says one request
 * went wrong. So it can always be dismissed by hand, it clears itself once a
 * request succeeds — a message about a failure that has since been superseded is
 * worse than no message — and it times out on its own so nothing is left pinned
 * to the top of the screen forever. The countdown pauses while the pointer is on
 * it or the close button has focus, because a message that vanishes mid-sentence
 * is its own bug. */
const NOTICE_LIFETIME_MS = 10000;
let noticeTimer;
let noticeRemainingMs = NOTICE_LIFETIME_MS;
let noticeHideAt = 0;

function showNotice(message) {
  const notice = el('notice');
  el('notice-text').textContent = message;
  notice.hidden = false;
  startNoticeCountdown();
}

function hideNotice() {
  clearTimeout(noticeTimer);
  el('notice').hidden = true;
}

/** Begin a full lifetime. Only a newly shown message gets one. */
function startNoticeCountdown() {
  armNoticeTimer(NOTICE_LIFETIME_MS);
  // Restarting the bar means dropping the animation, forcing a reflow so the
  // browser commits to its absence, then naming it again — reassigning a property
  // of a run that has already finished would leave the bar sitting at zero.
  // Assigned as one shorthand, so armNoticeTimer stays the only place the lifetime
  // is written down and the two cannot drift apart.
  const life = el('notice-life');
  life.style.animation = 'none';
  void life.offsetWidth;
  life.style.animation = `notice-drain ${NOTICE_LIFETIME_MS}ms linear forwards`;
  life.style.animationPlayState = '';
}

function armNoticeTimer(ms) {
  clearTimeout(noticeTimer);
  noticeRemainingMs = ms;
  noticeHideAt = Date.now() + ms;
  noticeTimer = setTimeout(hideNotice, ms);
}

function pauseNoticeCountdown() {
  if (el('notice').hidden) return;
  clearTimeout(noticeTimer);
  noticeRemainingMs = Math.max(0, noticeHideAt - Date.now());
  el('notice-life').style.animationPlayState = 'paused';
}

/* Resuming continues the time that was left, rather than granting another full
 * lifetime: pointer and focus events fire for all sorts of reasons that are not
 * "someone is reading this", and a fresh countdown on each of them would let a
 * dead message sit there indefinitely. The bar just un-pauses, so it stays honest
 * about how long is actually left. */
function resumeNoticeCountdown() {
  if (el('notice').hidden) return;
  el('notice-life').style.animationPlayState = '';
  armNoticeTimer(noticeRemainingMs);
}

/* ----------------------------------------------------------------- wiring */

let debounceTimer;
const debouncedSearch = () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => runSearch(), 250);
};

form.addEventListener('input', (event) => {
  // Keep the slider read-outs in step with their inputs.
  if (event.target.id === 'benchmark') updateBenchmarkHint();
  if (event.target.id === 'min-discount') el('discount-output').textContent = event.target.value;
  if (event.target.id === 'min-history') el('history-output').textContent = event.target.value;
  if (event.target.id === 'min-observations') el('liquidity-output').textContent = event.target.value;
  if (event.target.id === 'min-movement') el('movement-output').textContent = event.target.value;
  if (event.target.id === 'set-search') return;
  debouncedSearch();
});

form.addEventListener('submit', (event) => {
  event.preventDefault();
  runSearch();
});

el('sort').addEventListener('change', () => {
  applySortValue(el('sort').value);
  runSearch();
});

for (const button of sortButtons) {
  button.addEventListener('click', () => {
    // A fresh column starts ascending whatever it measures. Sorting a column the
    // grid is already sorted by can only mean "the other way".
    const isActive = state.sort === button.dataset.sort;
    state.sort = button.dataset.sort;
    state.isDescending = isActive ? !state.isDescending : false;
    syncSortViews();
    runSearch();
  });
}
el('load-more').addEventListener('click', loadMore);

el('notice-close').addEventListener('click', hideNotice);
el('notice').addEventListener('mouseenter', pauseNoticeCountdown);
el('notice').addEventListener('mouseleave', resumeNoticeCountdown);
// Keyboard equivalent of hovering: tabbing to the close button should not be a
// race against the timer.
el('notice-close').addEventListener('focus', pauseNoticeCountdown);
el('notice-close').addEventListener('blur', resumeNoticeCountdown);

el('set-search').addEventListener('input', (event) => {
  const needle = event.target.value.trim().toLowerCase();
  for (const label of el('set-list').children) {
    label.hidden = needle !== '' && !label.dataset.searchText.includes(needle);
  }
});

el('reset').addEventListener('click', () => {
  // Reset fires before the form clears, so re-read on the next tick.
  setTimeout(() => {
    syncRangeOutputs();
    el('set-search').value = '';
    for (const label of el('set-list').children) label.hidden = false;
    updateBenchmarkHint();
    // The address bar may still be carrying the shared link this session opened
    // with. Left there, a reload would undo the reset.
    history.replaceState(null, '', location.pathname);
    runSearch();
  }, 0);
});

/* The filters are all in the URL already once exported, so "export" is a copy
   plus putting that link in the address bar: the tab the user is looking at
   becomes bookmarkable and survives a reload, not just the pasted copy. */
let exportLabelTimer;

function reportExport(message) {
  const button = el('export-filters');
  clearTimeout(exportLabelTimer);
  button.textContent = message;
  button.classList.add('button--done');
  exportLabelTimer = setTimeout(() => {
    button.textContent = 'Export filters';
    button.classList.remove('button--done');
  }, 2000);
}

el('export-filters').addEventListener('click', async () => {
  const query = filterState().toString();
  const link = `${location.origin}${location.pathname}${query ? `?${query}` : ''}`;
  history.replaceState(null, '', link);
  try {
    await navigator.clipboard.writeText(link);
    reportExport(query ? 'Link copied' : 'Copied (no filters set)');
  } catch (error) {
    // Clipboard access can be refused outright — an insecure origin, or a
    // permission we have no way to ask for from here. The link is in the
    // address bar regardless, which is still an export.
    reportExport('Copy it from the address bar');
  }
});

el('detail-close').addEventListener('click', () => el('detail').close());
el('detail').addEventListener('click', (event) => {
  // Clicking the backdrop (the dialog element itself) dismisses.
  if (event.target === el('detail')) el('detail').close();
});

// The filter panel is a side rail on desktop and a collapsed disclosure on a
// phone. `open` is an attribute, not something CSS can set, so it is synced here.
// It ships open in the markup and is only ever *closed* for the narrow layout:
// if this script fails, the filters stay reachable rather than being sealed shut
// behind a summary that desktop CSS hides.
const narrowLayout = window.matchMedia('(max-width: 900px)');

function syncFilterPanel() {
  el('filters-panel').open = !narrowLayout.matches;
}

narrowLayout.addEventListener('change', syncFilterPanel);
syncFilterPanel();
syncSortViews();

// The startup calls are independent, so they go out together rather than making
// first paint wait for the sum of all three. The exception is a shared link:
// its set/rarity/finish ticks land on checkboxes that only exist once
// loadFilters has drawn them, so the first search has to wait for both.
const sharedLink = new URLSearchParams(location.search);
const restored = loadFilters().then(() => {
  if (location.search.length > 1) applyFilterState(sharedLink);
});
const firstSearch = location.search.length > 1
  ? restored.then(() => runSearch())
  : runSearch();

Promise.all([loadMeta(), restored, firstSearch]).catch((error) =>
  showNotice(`Could not initialise: ${error.message}`),
);
