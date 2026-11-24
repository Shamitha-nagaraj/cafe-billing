'use strict';

const $ = id => document.getElementById(id);
const state = {config: null, menu: [], cart: new Map(), category: 'All', pending: null, busy: false};
const pendingKey = 'cafe-ledger-pending-v1';
let toastTimer, reportVersion = 0;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function message(id, text = '') { $(id).textContent = text; $(id).hidden = !text; }
function toast(text) {
  message('toast', text); clearTimeout(toastTimer);
  toastTimer = setTimeout(() => message('toast'), 4500);
}
async function api(path, options = {}) {
  const response = await fetch(path, {credentials: 'same-origin', ...options,
    headers: {'Content-Type': 'application/json', 'X-Cafe-Request': '1', ...options.headers}});
  let data;
  try { data = await response.json(); } catch { data = {error: 'Unable to read the server response. Check your sign-in and connection.'}; }
  if (!response.ok) {
    const error = new Error(data.error || `Request failed (${response.status}).`);
    error.status = response.status; throw error;
  }
  return data;
}
function formatMoney(minor, currency = state.config.currency) {
  return new Intl.NumberFormat('en-IN', {style: 'currency', currency, maximumFractionDigits: 2}).format(minor / 100);
}
function dayLabel(value, options = {day: 'numeric', month: 'short'}) {
  return new Date(value + 'T12:00:00').toLocaleDateString('en-IN', options);
}
function timeLabel(value) {
  return new Date(value).toLocaleString('en-IN', {timeZone: state.config.timezone, day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'});
}
function shiftDay(value, days) {
  const date = new Date(value + 'T12:00:00Z'); date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}
function amountMinor(value) {
  if (!/^\d+(\.\d{1,2})?$/.test(value)) throw new Error('Enter a discount with up to two decimal places.');
  const [whole, fraction = ''] = value.split('.');
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
}
function lockControls() {
  const locked = !!state.pending;
  for (const id of ['discount', 'paymentMethod', 'orderType', 'clearCart', 'manageMenu']) $(id).disabled = locked;
  document.querySelectorAll('.menu-card,.quantity button').forEach(node => { node.disabled = locked; });
  $('checkout').disabled = state.busy || (!locked && state.cart.size === 0);
  $('checkout').textContent = state.busy ? 'Saving bill…' : locked ? 'Retry saving this bill ↗' : 'Complete bill ↗';
}
function renderMenu() {
  const active = state.menu.filter(item => item.active);
  const categories = ['All', ...new Set(active.map(item => item.category))];
  if (!categories.includes(state.category)) state.category = 'All';
  $('categories').replaceChildren(...categories.map(category => {
    const button = el('button', 'chip' + (category === state.category ? ' selected' : ''), category);
    button.setAttribute('aria-pressed', String(category === state.category));
    button.onclick = () => { state.category = category; renderMenu(); };
    return button;
  }));
  const query = $('menuSearch').value.trim().toLowerCase();
  const shown = active.filter(item => (state.category === 'All' || state.category === item.category) && (item.name + ' ' + item.category).toLowerCase().includes(query));
  $('menuGrid').replaceChildren(...shown.map(item => {
    const button = el('button', 'menu-card');
    button.setAttribute('aria-label', `Add ${item.name}, ${formatMoney(item.price_minor)}`);
    const symbol = el('span', 'menu-symbol', item.code); symbol.setAttribute('aria-hidden', 'true');
    const bottom = el('span', 'menu-bottom'); bottom.append(el('span', '', formatMoney(item.price_minor)), el('span', 'add-symbol', '+'));
    button.append(symbol, el('span', 'menu-name', item.name), bottom);
    button.onclick = () => {
      if (state.pending) return;
      const qty = state.cart.get(item.id) || 0;
      if (qty >= 99) return toast('Maximum 99 of one item per bill.');
      state.cart.set(item.id, qty + 1); renderCart();
    };
    return button;
  }));
  if (!shown.length) $('menuGrid').append(el('p', 'empty', 'No menu items match. Try another search or add an item.'));
  renderManagement(); lockControls();
}
function renderCart() {
  let subtotal = 0, count = 0;
  $('cartItems').replaceChildren();
  for (const [id, quantity] of state.cart) {
    const item = state.menu.find(item => item.id === id);
    if (!item) continue;
    subtotal += item.price_minor * quantity; count += quantity;
    const row = el('div', 'cart-row'), info = el('div');
    info.append(el('p', 'cart-name', item.name), el('p', 'cart-price', formatMoney(item.price_minor * quantity)));
    const controls = el('div', 'quantity');
    for (const change of [-1, 1]) {
      const button = el('button', '', change < 0 ? '−' : '+');
      button.setAttribute('aria-label', `${change < 0 ? 'Remove one' : 'Add one'} ${item.name}`);
      button.onclick = () => {
        if (state.pending) return;
        const next = quantity + change;
        if (next > 99) return;
        if (next) state.cart.set(id, next); else state.cart.delete(id);
        renderCart();
      };
      controls.append(button);
      if (change === -1) controls.append(el('span', '', String(quantity)));
    }
    row.append(info, controls); $('cartItems').append(row);
  }
  if (!state.cart.size) {
    const empty = el('p', 'empty'); empty.append(el('span', 'empty-symbol', '☕'), document.createTextNode('Something good is brewing. Add an item to begin.'));
    $('cartItems').append(empty);
  }
  let discount = 0, valid = true;
  try { discount = amountMinor($('discount').value); valid = discount <= subtotal; } catch { valid = false; }
  const tax = valid ? Math.floor(((subtotal - discount) * state.config.tax_bps + 5000) / 10000) : 0;
  $('cartCount').textContent = count;
  $('subtotal').textContent = formatMoney(subtotal);
  $('discountValue').textContent = valid ? '−' + formatMoney(discount) : 'Invalid';
  $('taxLabel').textContent = `Tax (${state.config.tax_bps / 100}%)`;
  $('taxValue').textContent = valid ? formatMoney(tax) : '—';
  $('totalValue').textContent = valid ? formatMoney(subtotal - discount + tax) : '—';
  lockControls(); if (!state.pending && !valid) $('checkout').disabled = true;
}
function renderManagement() {
  $('manageList').replaceChildren(...state.menu.map(item => {
    const row = el('div', 'manage-row'), info = el('div', '', item.name);
    info.append(el('small', '', `${item.category} · ${formatMoney(item.price_minor)}${item.active ? '' : ' · Inactive'}`));
    const edit = el('button', 'text-button', 'Edit'); edit.onclick = () => editMenu(item);
    row.append(info, edit); return row;
  }));
  $('categorySuggestions').replaceChildren(...[...new Set(state.menu.map(x => x.category))].map(category => {
    const option = el('option'); option.value = category; return option;
  }));
}
function editMenu(item = null) {
  if (state.pending) return toast('Finish saving the pending bill before editing the menu.');
  $('menuForm').reset(); message('menuError');
  $('menuDialogTitle').textContent = item ? 'Edit menu item' : 'Add menu item';
  $('menuId').value = item?.id || ''; $('itemName').value = item?.name || '';
  $('itemCategory').value = item?.category || 'Coffee';
  $('itemPrice').value = item ? (item.price_minor / 100).toFixed(2) : '';
  $('itemActive').checked = item ? !!item.active : true;
  $('menuDialog').showModal();
}
async function saveMenu(event) {
  event.preventDefault(); $('saveMenuItem').disabled = true; message('menuError');
  try {
    const id = $('menuId').value;
    await api('/api/menu' + (id ? '/' + id : ''), {method: id ? 'PATCH' : 'POST', body: JSON.stringify({name: $('itemName').value, category: $('itemCategory').value, price: $('itemPrice').value, active: $('itemActive').checked})});
    state.menu = (await api('/api/menu')).items;
    for (const key of state.cart.keys()) if (!state.menu.some(item => item.id === key && item.active)) state.cart.delete(key);
    renderMenu(); renderCart(); $('menuDialog').close(); toast('Menu saved. Current order uses the updated prices.');
  } catch (error) { message('menuError', error.message); }
  finally { $('saveMenuItem').disabled = false; }
}
async function checkout() {
  if (state.busy) return;
  message('cartError');
  if (!state.pending) {
    const payload = {request_id: crypto.randomUUID(), items: [...state.cart].map(([id, quantity]) => ({id, quantity})), discount: $('discount').value, payment_method: $('paymentMethod').value, order_type: $('orderType').value};
    state.pending = {payload, mode: state.config.demo, currency: state.config.currency};
    // Persist before sending: a lost response or page refresh must not create a second bill.
    try { sessionStorage.setItem(pendingKey, JSON.stringify(state.pending)); }
    catch { state.pending = null; return message('cartError', 'Browser storage is unavailable. Enable session storage before saving a bill.'); }
  }
  state.busy = true; lockControls();
  try {
    const {bill} = await api('/api/bills', {method: 'POST', body: JSON.stringify(state.pending.payload)});
    state.pending = null; sessionStorage.removeItem(pendingKey);
    state.cart.clear(); $('discount').value = '0'; showReceipt(bill); toast(`Saved ${bill.number}`);
  } catch (error) {
    if ([400, 404, 409, 413, 415, 422].includes(error.status)) {
      state.pending = null; sessionStorage.removeItem(pendingKey);
      message('cartError', error.message);
    } else {
      message('cartError', error.message + ' The order is locked because its save status is uncertain. Retry this same bill; do not collect payment again.');
    }
  } finally { state.busy = false; renderCart(); }
}
function showReceipt(bill) {
  const root = $('receipt'); root.replaceChildren();
  const head = el('div', 'receipt-head');
  head.append(el('h2', '', state.config.name), el('p', '', state.config.demo ? 'DEMO BILL · SYNTHETIC WORKSPACE' : 'Sales receipt'), el('p', '', bill.number));
  const meta = el('p', 'receipt-meta', `${timeLabel(bill.created_at)} · ${state.config.timezone}`);
  meta.append(el('br'), document.createTextNode(`${bill.order_type} · Payment recorded: ${bill.payment_method}`));
  const table = el('table'), header = el('thead'), headings = el('tr');
  ['Item', 'Qty', 'Amount'].forEach(text => headings.append(el('th', '', text))); header.append(headings);
  const body = el('tbody');
  for (const item of bill.items) {
    const row = el('tr'); row.append(el('td', '', `${item.name} (${formatMoney(item.unit_price_minor, bill.currency)} each)`), el('td', '', item.quantity), el('td', '', formatMoney(item.line_total_minor, bill.currency))); body.append(row);
  }
  table.append(header, body);
  const totals = el('div', 'totals');
  for (const [label, value, grand] of [['Subtotal', bill.subtotal_minor], ['Discount', -bill.discount_minor], [`Tax (${bill.tax_bps / 100}%)`, bill.tax_minor], ['Total', bill.total_minor, true]]) {
    const row = el('div', grand ? 'grand-total' : ''); row.append(el('span', '', label), el('strong', '', formatMoney(value, bill.currency))); totals.append(row);
  }
  root.append(head, meta, table, totals, el('p', 'receipt-footer', 'Thank you for stopping by.\nPayment is recorded by staff; this app does not verify payment.'));
  if (!$('receiptDialog').open) $('receiptDialog').showModal();
}
function chart(container, rows) {
  container.replaceChildren();
  const ns = 'http://www.w3.org/2000/svg';
  const svgNode = (name, attrs, text) => { const n = document.createElementNS(ns, name); for (const [key, value] of Object.entries(attrs)) n.setAttribute(key, value); if (text !== undefined) n.textContent = text; return n; };
  const svg = svgNode('svg', {viewBox: '0 0 620 260', role: 'img', 'aria-label': `Daily net sales, ${rows.length} days. Exact daily figures are available in Export CSV.`});
  const max = Math.max(100, ...rows.map(row => row.net_minor));
  for (let i = 0; i <= 3; i++) {
    const y = 20 + i * 63;
    svg.append(svgNode('line', {x1: 65, x2: 610, y1: y, y2: y, class: 'gridline'}));
    svg.append(svgNode('text', {x: 57, y: y + 4, 'text-anchor': 'end'}, new Intl.NumberFormat('en-IN', {notation: 'compact', maximumFractionDigits: 1}).format(max * (3 - i) / 300)));
  }
  const step = 545 / Math.max(rows.length, 1);
  rows.forEach((row, index) => {
    const height = row.net_minor / max * 189;
    const bar = svgNode('rect', {x: 65 + index * step + step * .15, y: 209 - height, width: Math.max(.5, step * .7), height, rx: Math.min(3, step * .1), class: 'bar'});
    bar.append(svgNode('title', {}, `${row.date}: ${formatMoney(row.net_minor)}`)); svg.append(bar);
    if (index === 0 || index === rows.length - 1 || (index % Math.max(1, Math.ceil(rows.length / 5)) === 0 && index < rows.length - rows.length / 8)) {
      svg.append(svgNode('text', {x: 65 + (index + .5) * step, y: 239, 'text-anchor': index === 0 ? 'start' : index === rows.length - 1 ? 'end' : 'middle'}, dayLabel(row.date)));
    }
  });
  container.append(svg);
}
async function loadReport() {
  const version = ++reportVersion; message('salesError');
  const query = new URLSearchParams({start: $('startDate').value, end: $('endDate').value});
  try {
    const data = await api('/api/analytics?' + query);
    if (version !== reportVersion) return;
    $('exportLink').href = '/api/export.csv?' + query;
    $('metrics').replaceChildren(...[['Net sales', formatMoney(data.totals.net_minor)], ['Completed bills', data.totals.bills], ['Average bill · incl. tax', formatMoney(data.totals.average_bill_minor)], ['Collected total · incl. tax', formatMoney(data.totals.gross_minor)]].map(([label, value]) => {
      const card = el('div', 'metric'); card.append(el('p', '', label), el('strong', '', value)); return card;
    }));
    chart($('salesChart'), data.daily);
    $('bestSellers').replaceChildren(...data.best_sellers.map((item, index) => {
      const row = el('div', 'seller'), name = el('span', 'seller-name');
      name.append(el('span', 'seller-rank', String(index + 1).padStart(2, '0')), document.createTextNode(item.name)); row.append(name, el('strong', '', `${item.quantity} sold`)); return row;
    }));
    if (!data.best_sellers.length) $('bestSellers').append(el('p', 'empty', 'Your first bill starts the story.'));
    $('recentBills').replaceChildren(...data.recent.map(bill => {
      const row = el('tr'); [bill.number, timeLabel(bill.created_at), bill.payment_method, formatMoney(bill.total_minor)].forEach(value => row.append(el('td', '', value)));
      const cell = el('td'), button = el('button', 'text-button', 'Receipt ↗');
      button.setAttribute('aria-label', `Open receipt ${bill.number}`);
      button.onclick = async () => { button.disabled = true; try { showReceipt((await api('/api/bills/' + bill.id)).bill); } catch (error) { message('salesError', error.message); } finally { button.disabled = false; } };
      cell.append(button); row.append(cell); return row;
    }));
    if (!data.recent.length) { const row = el('tr'), cell = el('td', 'empty', 'No bills in this date range.'); cell.colSpan = 5; row.append(cell); $('recentBills').append(row); }
  } catch (error) { if (version === reportVersion) message('salesError', error.message + ' Any figures still shown are from the last successful report.'); }
}
async function loadForecast() {
  $('forecastStatus').textContent = 'Training on completed days and checking the latest week…'; $('forecastContent').replaceChildren();
  try {
    const data = await api('/api/forecast');
    if (!data.ready) { $('forecastStatus').textContent = `${data.message} Current history: ${data.days} completed days.`; return; }
    $('forecastStatus').textContent = `${data.selected_method} had the lower error (or tied) on ${dayLabel(data.test_start)}–${dayLabel(data.test_end)}. Refit using ${data.days} completed days through ${dayLabel(data.trained_through)}. Forecast dates do not change with the sales filter.`;
    const summary = el('div', 'forecast-summary');
    for (const [label, value] of [['Suggested 7-day net sales', formatMoney(data.total_minor)], ['Ridge test MAE / day', formatMoney(data.model_mae_minor)], ['Baseline test MAE / day', formatMoney(data.baseline_mae_minor)]]) {
      const stat = el('div', 'forecast-stat'); stat.append(el('strong', '', value), el('span', '', label)); summary.append(stat);
    }
    const days = el('div', 'forecast-days');
    data.future.forEach(row => { const day = el('div', 'forecast-day', dayLabel(row.date, {weekday: 'short', day: 'numeric', month: 'short'})); day.append(el('strong', '', formatMoney(row.selected_minor))); days.append(day); });
    const details = el('details', 'forecast-details'); details.append(el('summary', '', 'Compare both methods and inspect the test week'));
    const futureTable = el('table'), header = el('tr'); ['Next week', 'Ridge', 'Baseline'].forEach(label => header.append(el('th', '', label))); futureTable.append(header);
    data.future.forEach(row => { const tr = el('tr'); [dayLabel(row.date), formatMoney(row.ridge_minor), formatMoney(row.baseline_minor)].forEach(value => tr.append(el('td', '', value))); futureTable.append(tr); });
    const testTable = el('table'), testHeader = el('tr'); ['Test day', 'Actual', 'Ridge', 'Baseline'].forEach(label => testHeader.append(el('th', '', label))); testTable.append(testHeader);
    data.holdout.forEach(row => { const tr = el('tr'); [dayLabel(row.date), formatMoney(row.actual_minor), formatMoney(row.ridge_minor), formatMoney(row.baseline_minor)].forEach(value => tr.append(el('td', '', value))); testTable.append(tr); });
    const wrap = el('div', 'table-wrap'); wrap.append(futureTable, testTable); details.append(wrap);
    $('forecastContent').append(summary, days, el('p', 'small-copy', data.note), details);
  } catch (error) { $('forecastStatus').textContent = 'Forecast unavailable: ' + error.message; }
}
async function start() {
  try {
    const [config, menu] = await Promise.all([api('/api/config'), api('/api/menu')]);
    state.config = config; state.menu = menu.items;
    $('brandName').textContent = config.name; document.title = config.name + ' · Billing & forecast';
    $('demoBanner').hidden = !config.demo; $('modeBadge').textContent = config.demo ? '● Demo mode' : '● Live register';
    $('businessDate').textContent = dayLabel(config.today, {weekday: 'long', day: 'numeric', month: 'short'});
    $('endDate').value = config.today; $('startDate').value = shiftDay(config.today, -29);
    $('startDate').max = config.today; $('endDate').max = config.today;
    try {
      const stored = JSON.parse(sessionStorage.getItem(pendingKey) || 'null');
      if (stored) {
        if (stored.mode !== config.demo || stored.currency !== config.currency) throw new Error('An unfinished bill belongs to another workspace. Return to that mode and resolve it before billing here.');
        state.pending = stored;
        state.cart = new Map(stored.payload.items.map(item => [item.id, item.quantity]));
        $('discount').value = stored.payload.discount; $('paymentMethod').value = stored.payload.payment_method; $('orderType').value = stored.payload.order_type;
        message('cartError', 'Recovered a pending bill. Retry saving this same bill to retrieve its receipt; do not collect payment again.');
      }
    } catch (error) { message('globalError', error.message); $('registerView').hidden = true; return; }
    renderMenu(); renderCart();
    $('menuSearch').oninput = renderMenu; $('discount').oninput = renderCart;
    $('manageMenu').onclick = () => { $('menuManagement').hidden = !$('menuManagement').hidden; };
    $('addMenuItem').onclick = () => editMenu(); $('menuForm').onsubmit = saveMenu;
    $('closeMenuDialog').onclick = () => $('menuDialog').close();
    $('closeReceipt').onclick = () => $('receiptDialog').close(); $('printReceipt').onclick = () => window.print();
    $('checkout').onclick = checkout;
    $('clearCart').onclick = () => { if (state.pending) return; state.cart.clear(); $('discount').value = '0'; message('cartError'); renderCart(); };
    for (const id of ['registerTab', 'salesTab']) $(id).onclick = () => {
      const sales = id === 'salesTab'; $('registerView').hidden = sales; $('salesView').hidden = !sales;
      for (const tab of ['registerTab', 'salesTab']) { $(tab).classList.toggle('active', tab === id); $(tab).setAttribute('aria-pressed', String(tab === id)); }
      if (sales) { loadReport(); loadForecast(); }
    };
    $('periodForm').onsubmit = event => { event.preventDefault(); loadReport(); };
  } catch (error) { message('globalError', 'Unable to open the register: ' + error.message + ' Refresh after fixing the connection.'); }
}
start();
