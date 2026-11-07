'use strict';
const $ = selector => document.querySelector(selector);
const money = value => new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR', maximumFractionDigits: 2 }).format(value / 100);
const labels = { sale: 'Customer payment', refund: 'Refund', expense: 'Operating expense', income_tax: 'Income tax paid', owner_deposit: 'Owner contribution', owner_draw: 'Owner withdrawal' };
let state = null;
let token = '';
let loading = false;
const element = (tag, text, cls) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; };
function empty(title, body) { const node = element('div', undefined, 'empty'); node.append(element('strong', title), element('p', body)); return node; }
async function request(path, payload) {
  const response = await fetch(path, payload === undefined ? { cache: 'no-store' } : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Session-Token': token }, body: JSON.stringify(payload) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Could not load local records.');
  return result;
}
async function refresh() {
  if (loading) return false;
  loading = true;
  try {
    state = await request(`/api/snapshot?scope=${encodeURIComponent($('#scope').value)}&venture=${encodeURIComponent($('#venture').value)}`);
    render();
    $('#status').textContent = '';
    return true;
  } catch (error) { $('#status').textContent = error.message; return false; }
  finally { loading = false; }
}
function syncChoices(select, options) {
  const value = select.value;
  select.replaceChildren(...options.map(([id, name]) => { const item = element('option', name); item.value = id; return item; }));
  if ([...select.options].some(item => item.value === value)) select.value = value;
}
function render() {
  const t = state.totals;
  const launch = state.launch;
  if (launch) {
    const published = launch.public_deployment_status === 'published';
    $('#launch-heading').textContent = published ? 'Website live' : launch.publication_approved ? 'Publication approved' : launch.offer_approved && launch.name_status === 'approved' && launch.email_status === 'created' ? 'Name and email confirmed' : launch.offer_approved ? 'Offer approved' : 'Offer approval pending';
    $('#identity-contact').textContent = `${launch.working_name} · ${launch.email_status === 'created' && launch.actual_email ? launch.actual_email : 'Business email pending'}`;
    $('#offer-caption').textContent = `${launch.offer_approved ? 'Reporting offer approved' : 'Offer approval pending'} · real payments shown below`;
    const steps = [];
    if (!['cleared', 'not_required'].includes(launch.manager_clearance)) steps.push('manager clearance');
    if (launch.name_status !== 'approved') steps.push('business name approval');
    if (launch.email_status !== 'created') steps.push('email setup');
    const nextStage = published ? 'first customer discovery' : launch.publication_approved ? 'owner setup pending' : 'launch review next';
    $('#launch-note').textContent = `R0 upfront budget · 3 hours a week · ${steps.length ? steps.join(', ') + ' pending' : nextStage}`;
    const customerPage = $('#customer-page');
    customerPage.href = 'http://127.0.0.1:8766/';
    customerPage.textContent = 'Open customer-page preview';
    if (published && launch.public_website_url) {
      try {
        const publicURL = new URL(launch.public_website_url);
        if (publicURL.protocol === 'https:') {
          customerPage.href = publicURL.href;
          customerPage.textContent = 'Open public customer page';
        }
      } catch (_) { /* Keep the local preview if the saved URL is invalid. */ }
    }
  }
  $('#receipts').textContent = money(t.receipts_cents);
  $('#expenses').textContent = money(t.expenses_cents);
  $('#surplus').textContent = money(t.cash_surplus_cents);
  $('#reserve').textContent = t.reserve_target_cents === null ? 'Unset' : money(t.reserve_target_cents);
  $('#budget-note').textContent = `${money(state.settings.monthly_budget_cents)} monthly budget`;
  $('#period-note').textContent = `${state.start ? state.start : 'First record'} to ${state.as_of} · SA tax year ending February ${state.tax_year_end} · refunds ${money(t.refunds_cents)} · income tax paid ${money(t.income_tax_paid_cents)}`;
  syncChoices($('#venture'), [['all', 'All ventures'], ...state.ventures.map(v => [v.id, v.name])]);
  document.querySelectorAll('.venture-input').forEach(select => syncChoices(select, state.ventures.map(v => [v.id, v.name])));
  const visibleVentures = state.ventures.filter(v => $('#venture').value === 'all' || v.id === $('#venture').value);
  $('#venture-cards').replaceChildren(...visibleVentures.map(v => {
    const card = element('article', undefined, 'venture-card');
    const top = element('div', undefined, 'venture-top'); top.append(element('h3', v.name), element('span', v.status, 'badge'));
    const numbers = element('div', undefined, 'venture-numbers');
    for (const [label, amount] of [['Payments', v.receipts_cents], ['Cash surplus', v.cash_surplus_cents]]) { const block = element('div'); block.append(element('small', label), element('strong', money(amount))); numbers.append(block); }
    card.append(top, element('p', v.offer), numbers, element('p', `${money(v.price_cents)} ${v.status === 'Offer approved' ? 'approved pilot price' : 'proposed test price'} · ${v.note}`, 'offer-price'));
    return card;
  }));
  $('#alerts').replaceChildren(...state.alerts.map(a => element('li', a.text, a.level === 'info' ? 'info' : '')));
  const vat = state.vat_monitor;
  $('#vat-value').textContent = `${money(vat.recorded_receipts_ex_vat_cents)} / ${money(vat.threshold_cents)}`;
  $('#vat-progress').value = Math.max(0, vat.recorded_receipts_ex_vat_cents);
  renderChart(); renderLedger(); renderPipeline();
  $('#refreshed').textContent = `Updated ${new Date().toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })}`;
}
function renderChart() {
  const groups = new Map();
  for (const row of state.entries) {
    if (row.void_reason || !['sale', 'expense'].includes(row.kind)) continue;
    const month = row.date.slice(0, 7);
    if (!groups.has(month)) groups.set(month, { sale: 0, expense: 0 });
    groups.get(month)[row.kind] += row.amount_cents;
  }
  if (!groups.size) { $('#chart').replaceChildren(empty('No money recorded yet', 'Your first payment or expense will appear here.')); return; }
  const data = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0])).slice(-8);
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', '0 0 560 250'); svg.setAttribute('role', 'img');
  const title = document.createElementNS(ns, 'title'); title.textContent = 'Monthly customer payments and operating expenses'; svg.append(title);
  const maximum = Math.max(1, ...data.flatMap(([, v]) => [v.sale, v.expense]));
  const step = 470 / data.length;
  for (let i = 0; i < 4; i++) { const y = 20 + i * 58; const line = document.createElementNS(ns, 'line'); for (const [k, v] of Object.entries({ x1: 65, x2: 545, y1: y, y2: y, stroke: '#e5ebf3' })) line.setAttribute(k, v); svg.append(line); }
  data.forEach(([month, values], i) => {
    const x = 69 + i * step;
    for (const [kind, color, offset] of [['sale', '#174cd3', 0], ['expense', '#f39c46', 21]]) {
      const height = values[kind] / maximum * 165;
      const rect = document.createElementNS(ns, 'rect');
      for (const [k, v] of Object.entries({ x: x + offset, y: 194 - height, width: 17, height, rx: 3, fill: color })) rect.setAttribute(k, v);
      const tooltip = document.createElementNS(ns, 'title'); tooltip.textContent = `${month}: ${labels[kind]} ${money(values[kind])}`; rect.append(tooltip); svg.append(rect);
    }
    const text = document.createElementNS(ns, 'text'); text.setAttribute('x', x + 19); text.setAttribute('y', '218'); text.setAttribute('font-size', '13'); text.setAttribute('text-anchor', 'middle'); text.setAttribute('fill', '#58687b'); text.textContent = month.slice(5) + '/' + month.slice(2, 4); svg.append(text);
  });
  $('#chart').replaceChildren(svg);
}
function renderLedger() {
  $('#records-count').textContent = `${state.entries.length} record${state.entries.length === 1 ? '' : 's'}`;
  if (!state.entries.length) { const td = element('td'); td.colSpan = 6; td.append(empty('Start with a real payment', 'Quotes and test prices belong in the pipeline.')); const tr = element('tr'); tr.append(td); $('#ledger').replaceChildren(tr); return; }
  $('#ledger').replaceChildren(...state.entries.map(row => {
    const tr = element('tr', undefined, row.void_reason ? 'voided' : '');
    const ref = element('td', row.venture_name); ref.append(element('small', row.reference), element('small', row.description));
    const evidence = element('td', row.evidence || 'Missing');
    const correction = element('td');
    if (row.void_reason) correction.append(element('small', `Corrected: ${row.void_reason}`));
    else { const button = element('button', 'Correct', 'text-button'); button.type = 'button'; button.addEventListener('click', () => { $('#correction-form').elements.id.value = row.id; openDialog('#correction-dialog'); }); correction.append(button); }
    tr.append(element('td', row.date), ref, element('td', labels[row.kind]), element('td', money(row.amount_cents), 'numeric'), evidence, correction);
    return tr;
  }));
}
function renderPipeline() {
  const items = state.opportunities.filter(item => item.stage !== 'Closed');
  if (!items.length) { $('#pipeline').replaceChildren(empty('No open opportunities', 'Add a customer who has asked to discuss the offer.')); return; }
  $('#pipeline').replaceChildren(...items.map(item => {
    const row = element('div', undefined, 'pipeline-row');
    const customer = element('div', item.customer); customer.append(element('small', state.ventures.find(v => v.id === item.venture_id)?.name || item.venture_id));
    const next = element('div', item.next_action); next.append(element('small', item.consent_note));
    const close = element('button', 'Close', 'text-button'); close.addEventListener('click', async () => { close.disabled = true; try { await request('/api/close-opportunity', { id: item.id }); await refresh(); } catch (e) { $('#status').textContent = e.message; close.disabled = false; } });
    row.append(customer, element('span', money(item.value_cents)), element('span', item.stage, 'badge'), next, close); return row;
  }));
}
function openDialog(selector) { const dialog = $(selector); dialog.querySelector('.form-error').textContent = ''; dialog.showModal(); }
function configurePaymentFields() {
  const refund = $('#entry-kind').value === 'refund';
  $('#related-label').hidden = !refund; $('#related-sale').required = refund;
  $('#entry-vat').disabled = state?.settings.vat_status !== 'registered' || !['sale', 'refund'].includes($('#entry-kind').value);
  if ($('#entry-vat').disabled) $('#entry-vat').value = '0';
  $('#vat-hint').textContent = state?.settings.vat_status === 'registered' ? 'Record VAT already included in this payment.' : 'Owner confirmed no VAT registration. Do not charge VAT.';
}
function bindForm(selector, path, transform = value => value) {
  const form = $(selector);
  form.addEventListener('submit', async event => {
    event.preventDefault(); const button = form.querySelector('[type=submit]'); button.disabled = true;
    try { await request(path, transform(Object.fromEntries(new FormData(form)))); form.closest('dialog').close(); form.reset(); await refresh(); }
    catch (error) { form.querySelector('.form-error').textContent = error.message; }
    finally { button.disabled = false; }
  });
}
$('#add-money').addEventListener('click', () => {
  if (!state) return;
  const form = $('#entry-form'); form.elements.date.value = state.as_of; form.elements.date.max = state.as_of;
  // Refund links include all active payments, even when the visible period hides them.
  request('/api/snapshot?scope=all&venture=all').then(all => {
    syncChoices($('#related-sale'), [['', 'Choose original payment'], ...all.entries.filter(r => r.kind === 'sale' && !r.void_reason).map(r => [r.id, `${r.reference} · ${money(r.amount_cents)}`])]);
    configurePaymentFields(); openDialog('#entry-dialog');
  }).catch(error => { $('#status').textContent = error.message; });
});
$('#entry-kind').addEventListener('change', configurePaymentFields);
$('#settings-button').addEventListener('click', () => {
  if (!state) return; const f = $('#settings-form'); f.elements.vat_status.value = state.settings.vat_status; f.elements.reserve_percent.value = state.settings.reserve_percent ?? ''; f.elements.monthly_budget.value = state.settings.monthly_budget_cents / 100; openDialog('#settings-dialog');
});
$('#add-opportunity').addEventListener('click', () => { if (state) openDialog('#opportunity-dialog'); });
document.querySelectorAll('.close-dialog').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
$('#scope').addEventListener('change', refresh); $('#venture').addEventListener('change', refresh);
bindForm('#entry-form', '/api/entry', value => { if (value.kind !== 'refund') delete value.related_id; value.vat = value.vat || '0'; return value; });
bindForm('#settings-form', '/api/settings', value => ({ ...value, reserve_percent: value.reserve_percent === '' ? null : value.reserve_percent }));
bindForm('#opportunity-form', '/api/opportunity'); bindForm('#correction-form', '/api/void');
(async () => { try { token = (await request('/api/bootstrap')).token; await refresh(); } catch (e) { $('#status').textContent = e.message; } })();
setInterval(() => { if (!document.hidden && !document.querySelector('dialog[open]')) refresh(); }, 30000);
// Read-only browser tool, where supported. Never exposes money-recording actions to agents.
if (document.modelContext?.registerTool) {
  try { Promise.resolve(document.modelContext.registerTool({
    name: 'get_business_cash_report', title: 'Business cash report',
    description: 'Read the current local management cash report. All amounts are integer ZAR cents; it is not a tax return.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, untrustedContentHint: true },
    execute: async input => { if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).length) throw new Error('No arguments expected.'); if (!(await refresh()) || !state) throw new Error('Local records unavailable or refreshing; try again.'); return { as_of: state.as_of, totals: state.totals, ventures: state.ventures, alerts: state.alerts, note: state.note }; }
  })).catch(() => {}); } catch (_) { /* Ordinary dashboard remains available. */ }
}
