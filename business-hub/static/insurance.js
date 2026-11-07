// Quote Lab deliberately keeps the intake and the pricing engine separate.
// This file handles the form. hub/insurance.py owns validation and calculation.
const form = document.querySelector('#quote-form');
const steps = ['vehicle', 'extras', 'driver', 'cover'];
const state = { step: 0, session: null, config: null, report: null, sequence: 0, controller: null, timer: null, calculating: false, stale: true, preset: 'known', hypothetical: false };
const numericFields = ['year', 'vehicleValue', 'driverAge', 'licenceYears', 'claimsLast3Years', 'annualKm', 'excess'];
const stringFields = ['make', 'model', 'variant', 'colour', 'paintFinish', 'valuationBasis', 'locationDescription', 'usage', 'overnightParking', 'tracker', 'finance', 'coverType', 'carHire', 'creditShortfall', 'modifications'];

function escapeHtml(value = '') {
  return String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
}

function money(value) {
  return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(Number(value) || 0);
}

function signedMoney(value) {
  return `${value > 0 ? '+' : value < 0 ? '−' : ''}${money(Math.abs(value))}`;
}

function nullableNumber(value) { return value === '' || value === undefined || value === null ? null : Number(value); }
function nullableBoolean(value) { return value === 'true' ? true : value === 'false' ? false : null; }

// Only the vehicle facts in this profile were supplied by the user.
function knownVehicle() {
  return {
    make: 'Volkswagen', model: 'Polo', variant: 'GTI', year: 2026,
    vehicleValue: 620000, colour: 'White', paintFinish: 'unknown', valuationBasis: 'unknown',
    locationDescription: '', driverAge: null, licenceYears: null, claimsLast3Years: null,
    annualKm: null, usage: 'unknown', overnightParking: 'unknown', tracker: 'unknown',
    finance: 'unknown', coverType: 'unknown', excess: null, carHire: 'unknown',
    creditShortfall: 'unknown', modifications: 'none', extrasConfirmed: null,
    extras: [{ name: 'Factory sunroof', category: 'factory', value: null, includedInVehicleValue: true }],
  };
}

function profileForPreset(preset) {
  const profile = knownVehicle();
  if (preset === 'basic') {
    // Simulates stopping at minimal vehicle information. It is not a competitor quote.
    Object.assign(profile, { variant: '', colour: '', modifications: 'unknown', extras: [] });
  }
  if (preset === 'whatif') {
    // Every driver/use/cover answer below is fictional, for the demonstration only.
    Object.assign(profile, {
      paintFinish: 'standard', valuationBasis: 'retail', locationDescription: 'Example area — Johannesburg',
      driverAge: 24, licenceYears: 2, claimsLast3Years: 0, annualKm: 24000,
      usage: 'business', overnightParking: 'driveway', tracker: 'none', finance: 'financed',
      coverType: 'comprehensive', excess: 5000, carHire: 'yes', creditShortfall: 'yes', extrasConfirmed: true,
    });
    profile.extras.push({ name: 'What-if aftermarket wheels', category: 'aftermarket', value: 25000, includedInVehicleValue: false });
  }
  return profile;
}

function readExtras() {
  return [...document.querySelectorAll('.extra-row')].map(row => ({
    name: row.querySelector('[data-extra-field="name"]').value.trim(),
    category: row.querySelector('[data-extra-field="category"]').value,
    value: nullableNumber(row.querySelector('[data-extra-field="value"]').value),
    includedInVehicleValue: nullableBoolean(row.querySelector('[data-extra-field="includedInVehicleValue"]').value),
  }));
}

function readProfile() {
  const values = new FormData(form);
  const profile = {};
  for (const name of stringFields) profile[name] = String(values.get(name) ?? '').trim();
  for (const name of numericFields) profile[name] = nullableNumber(values.get(name));
  profile.extrasConfirmed = nullableBoolean(values.get('extrasConfirmed'));
  profile.extras = readExtras();
  return profile;
}

function renderExtras(extras) {
  const categories = { factory: 'Factory option', aftermarket: 'Aftermarket accessory', paint: 'Custom paint / wrap', performance: 'Performance change' };
  document.querySelector('#extras-list').innerHTML = extras.length ? extras.map((extra, index) => `
    <article class="extra-row" data-extra-index="${index}">
      <div class="extra-top"><span class="extra-label">EXTRA ${String(index + 1).padStart(2, '0')}</span><button class="extra-remove" type="button" data-remove-extra="${index}" aria-label="Remove extra ${index + 1}">Remove ×</button></div>
      <div class="extra-fields">
        <label class="field extra-name">Name<input data-extra-field="name" value="${escapeHtml(extra.name)}" maxlength="120" required placeholder="For example: factory sunroof"></label>
        <label class="field extra-category">Type<select data-extra-field="category">${Object.entries(categories).map(([key, label]) => `<option value="${key}" ${extra.category === key ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
        <label class="field extra-value">Separate value (R)<input data-extra-field="value" value="${extra.value ?? ''}" type="number" min="0" max="1000000" step="1" placeholder="Unknown / not needed"></label>
        <label class="field extra-included">Already in vehicle value?<select data-extra-field="includedInVehicleValue"><option value="unknown" ${extra.includedInVehicleValue === null ? 'selected' : ''}>Not sure</option><option value="true" ${extra.includedInVehicleValue === true ? 'selected' : ''}>Yes, already included</option><option value="false" ${extra.includedInVehicleValue === false ? 'selected' : ''}>No, add its value once</option></select></label>
      </div>
      <p class="extra-help">A separate cost can stay blank when this item is already included in the vehicle value.</p>
    </article>`).join('') : '<div class="empty-extras"><p>No extras listed yet. Confirm below if none are fitted.</p></div>';
  document.querySelector('#add-extra').disabled = extras.length >= 20;
  updateSunroofNote();
}

function updateSunroofNote() {
  const note = document.querySelector('.included-note');
  const sunroof = readExtras().find(extra => /sunroof/i.test(extra.name));
  note.hidden = !sunroof || sunroof.includedInVehicleValue !== true;
  if (sunroof?.includedInVehicleValue === true) {
    note.querySelector('p').innerHTML = `The sunroof is marked as already included in the ${escapeHtml(money(form.elements.vehicleValue.value))} vehicle value. Its separate cost can stay blank; the demo adds <strong>R0</strong> for it.`;
  }
}

function setProfile(profile) {
  for (const name of [...stringFields, ...numericFields]) form.elements[name].value = profile[name] ?? '';
  form.elements.extrasConfirmed.value = profile.extrasConfirmed === null ? 'unknown' : String(profile.extrasConfirmed);
  renderExtras(profile.extras || []);
}

function showStep(index) {
  state.step = Math.max(0, Math.min(steps.length - 1, index));
  const step = steps[state.step];
  for (const section of document.querySelectorAll('[data-section]')) section.hidden = section.dataset.section !== step;
  for (const button of document.querySelectorAll('[data-step]')) {
    const active = button.dataset.step === step;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current');
  }
  document.querySelector('#step-counter').textContent = `Step ${state.step + 1} of ${steps.length}`;
  document.querySelector('#previous-step').hidden = state.step === 0;
  document.querySelector('#next-step').hidden = state.step === steps.length - 1;
}

function setFormError(message = '') {
  const element = document.querySelector('#form-error');
  element.textContent = message;
  element.hidden = !message;
}

function setReportActions(enabled) {
  document.querySelector('#download-report').disabled = !enabled;
  document.querySelector('#print-report').disabled = !enabled;
}

function invalidateReport() {
  state.stale = true;
  ++state.sequence;
  state.controller?.abort();
  clearTimeout(state.timer);
  state.calculating = false;
  document.querySelector('#calculate-button').disabled = false;
  document.querySelector('#result-status').textContent = 'Update needed';
  document.querySelector('#result-status').className = 'status-chip stale-status';
  document.querySelector('#form-status').textContent = 'Details changed — updating the demo estimate…';
  document.querySelector('#report-content').classList.add('report-stale');
  setReportActions(false);
}

function scheduleCalculation() {
  if (!state.session) return;
  invalidateReport();
  state.timer = setTimeout(() => calculateEstimate(false), 650);
}

function markEdited() {
  state.preset = 'edited';
  for (const button of document.querySelectorAll('[data-preset]')) {
    button.classList.remove('active'); button.setAttribute('aria-pressed', 'false');
  }
  document.querySelector('#scenario-note').textContent = state.hypothetical
    ? 'You are editing fictional what-if answers. They are not your personal details.'
    : 'Current entered profile. The original vehicle facts came from you; new answers are the values entered here.';
}

function validateBrowserInputs(showErrors) {
  const invalid = [...form.querySelectorAll('input,select')].find(input => !input.checkValidity());
  if (!invalid) return true;
  document.querySelector('#form-status').textContent = 'Complete or correct the highlighted field to update the result.';
  if (showErrors) {
    const section = invalid.closest('[data-section]');
    if (section) showStep(steps.indexOf(section.dataset.section));
    invalid.reportValidity();
    setFormError('Please correct the highlighted field. Unknown optional answers can remain blank.');
  }
  return false;
}

async function calculateEstimate(showErrors = true) {
  clearTimeout(state.timer);
  if (!state.session || !validateBrowserInputs(showErrors)) return;
  const profile = readProfile();
  const sequence = ++state.sequence;
  state.controller?.abort();
  state.controller = new AbortController();
  state.calculating = true;
  setFormError();
  document.querySelector('#calculate-button').disabled = true;
  document.querySelector('#result-status').textContent = 'Calculating';
  document.querySelector('#form-status').textContent = 'Calculating with the supplied details…';
  setReportActions(false);
  try {
    const response = await fetch('/api/insurance/estimate', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.session.csrfToken },
      body: JSON.stringify(profile), signal: state.controller.signal,
    });
    const report = await response.json();
    if (!response.ok) throw new Error(report.error || 'Could not calculate the demo estimate.');
    if (sequence !== state.sequence) return;
    state.report = report;
    state.stale = false;
    renderReport(report);
    setReportActions(true);
    document.querySelector('#form-status').textContent = 'Demo calculation updated. Review the unanswered and unpriced details.';
  } catch (error) {
    if (error.name === 'AbortError' || sequence !== state.sequence) return;
    setFormError(error.message);
    document.querySelector('#result-status').textContent = 'Needs correction';
    document.querySelector('#form-status').textContent = 'The previous result is out of date until these details are corrected.';
  } finally {
    if (sequence === state.sequence) {
      state.calculating = false;
      document.querySelector('#calculate-button').disabled = false;
    }
  }
}

function renderReport(report) {
  document.querySelector('#result-empty').hidden = true;
  const content = document.querySelector('#report-content');
  content.hidden = false;
  content.classList.remove('report-stale');
  document.querySelector('#benchmark-amount').textContent = money(report.benchmarkMonthly);
  document.querySelector('#detailed-amount').textContent = money(report.illustrativeMonthly);
  document.querySelector('#detail-title').textContent = report.completeness.percent === 100 ? 'Detailed demo total' : 'Known-input demo subtotal';
  document.querySelector('#difference-line').textContent = report.differenceMonthly === 0
    ? 'Same demo subtotal. Unanswered and unpriced details still need review.'
    : `${signedMoney(report.differenceMonthly)} / month${report.differencePercent === null ? '' : ` (${report.differencePercent > 0 ? '+' : ''}${Number(report.differencePercent).toFixed(1)}%)`} with the current demo assumptions.`;
  document.querySelector('#estimate-range').textContent = `${money(report.range.low)} – ${money(report.range.high)} / month`;
  document.querySelector('#range-explanation').textContent = `Arbitrary ±${report.range.marginPercent}% demo band. It is uncalibrated and is not a confidence interval or a guarantee. See the full formula under assumptions.`;
  document.querySelector('#completeness-value').textContent = `${report.completeness.percent}%`;
  const progress = document.querySelector('#completeness-bar');
  progress.setAttribute('aria-valuenow', String(report.completeness.percent));
  progress.querySelector('span').style.width = `${report.completeness.percent}%`;
  document.querySelector('#completeness-note').textContent = `${report.completeness.answered} of ${report.completeness.total} intake checks answered. This measures input coverage, not premium accuracy or approval.`;
  document.querySelector('#vehicle-value-summary').textContent = money(report.declaredVehicleValue);
  document.querySelector('#extras-value-summary').textContent = money(report.extrasAddedValue);
  document.querySelector('#insured-value-summary').textContent = money(report.insuredValueForDemo);
  document.querySelector('#extras-summary').innerHTML = report.extrasSummary.length ? report.extrasSummary.map(extra => `
    <div class="extra-summary-row"><div><strong>${escapeHtml(extra.name)}</strong><small>${extra.status === 'included' ? 'Already included · counted once' : extra.status === 'added' ? 'Added once to the demo value' : 'Cost or inclusion needs review'}</small></div><span>${extra.status === 'unpriced' ? 'Unpriced' : signedMoney(extra.addedValue)}</span></div>`).join('') : '<p class="summary-empty">No extra values added. Check whether the inventory is complete.</p>';
  document.querySelector('#breakdown-list').innerHTML = report.breakdown.map(item => `
    <div class="breakdown-row"><div><strong>${escapeHtml(item.label)}</strong><p>${escapeHtml(item.explanation)}</p><small>${money(item.before)} → ${money(item.after)}${item.factor !== null && item.factor !== undefined ? ` · ×${item.factor}` : ''}</small></div><span class="breakdown-amount">${item.kind === 'base' ? money(item.after) : signedMoney(item.amount)}</span></div>`).join('');
  document.querySelector('#review-count').textContent = report.reviewItems.length;
  document.querySelector('#review-list').innerHTML = report.reviewItems.map(item => `
    <li class="review-item"><span class="review-marker" aria-hidden="true">${item.severity === 'unknown' ? '?' : '!'}</span><div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.detail)}</p></div></li>`).join('');
  document.querySelector('#missing-count').textContent = report.completeness.missing.length;
  document.querySelector('#missing-list').innerHTML = report.completeness.missing.length
    ? report.completeness.missing.map(item => `<li>${escapeHtml(item.label)}</li>`).join('')
    : '<li>All intake checks are answered. Insurer pricing and acceptance still need verification.</li>';
  const displayedAssumptions = [...report.assumptions, report.range.basis];
  document.querySelector('#assumptions-list').innerHTML = displayedAssumptions.map(item => `<li>${escapeHtml(item)}</li>`).join('');
  document.querySelector('#model-note').textContent = `${report.meta.notice} Model: ${report.meta.modelVersion}.`;
  document.querySelector('#result-status').textContent = report.completeness.percent === 100 ? 'Inputs complete · review required' : 'Provisional · details missing';
  document.querySelector('#result-status').className = 'status-chip';
}

function renderRules(config) {
  document.querySelector('#pricing-notice').textContent = `The ${money(config.referenceMonthlyPremium)} starting reference and all pricing rules are illustrative. This is not an insurer quote.`;
  const labels = { driverAge: 'Driver age', licenceYears: 'Licence experience', claimsLast3Years: 'Claims in 3 years', annualKm: 'Distance', usage: 'Use', overnightParking: 'Parking', tracker: 'Tracking', coverType: 'Cover type', excess: 'Excess' };
  const conditions = { under25: 'Under 25', '25AndOver': '25 or older', under3: 'Under 3 years', '3AndOver': '3+ years', '0': 'No claims', '1': 'One claim', '2AndOver': 'Two or more claims', upTo10000: 'Up to 10,000 km', upTo20000: '10,001–20,000 km', over20000: 'Over 20,000 km', private: 'Private / commuting', business: 'Business', delivery: 'Delivery / commercial', garage: 'Locked garage', secured: 'Secured premises', driveway: 'Driveway', street: 'Street', active: 'Active tracker', none: 'No tracker', comprehensive: 'Comprehensive', third_party_fire_theft: 'Third party, fire & theft', third_party: 'Third party', under2500: 'Below R2,500', upTo5000: 'R2,500–5,000', over5000: 'Over R5,000' };
  const rows = Object.entries(config.factors || {}).flatMap(([group, factors]) => Object.entries(factors).map(([condition, factor]) => `<tr><td>${escapeHtml(labels[group] || group)}</td><td>${escapeHtml(conditions[condition] || condition)}</td><td>×${factor}</td></tr>`));
  document.querySelector('#rules-content').innerHTML = `
    <div class="rules-baseline"><strong>${money(config.referenceMonthlyPremium)} / month</strong><p>Illustrative reference for a vehicle valued at ${money(config.referenceVehicleValue)}. ${escapeHtml(config.referenceExplanation)}</p></div>
    <div class="rules-table-wrap"><table class="rules-table"><thead><tr><th>Demo factor</th><th>Answer</th><th>Multiplier</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>
    <p class="rules-options">Demo optional additions: car hire ${money(config.optionalMonthly.carHire)} / month; credit shortfall ${money(config.optionalMonthly.creditShortfall)} / month when financed. These are fictional amounts.</p>
    <p>${escapeHtml(config.scenarioBand.explanation)}</p>
    <h3>Captured for review, not priced</h3><ul>${config.unpricedChecks.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
    <h3>Field-selection sources</h3><p>These insurer pages inform which questions are asked. No numerical tariff comes from them.</p><ul>${config.sources.filter(source => /^https:\/\//.test(source.url)).map(source => `<li><a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">${escapeHtml(source.title)} ↗</a> — ${escapeHtml(source.purpose)}</li>`).join('')}</ul>
    <details><summary>Full local rule configuration</summary><pre class="rules-json">${escapeHtml(JSON.stringify(config, null, 2))}</pre></details>`;
}

function setPreset(preset) {
  state.preset = preset;
  state.hypothetical = preset === 'whatif';
  setProfile(profileForPreset(preset));
  const notes = {
    basic: 'Minimal vehicle intake only. This uses a fictional starting reference, not a Hippo or insurer quote.',
    known: 'Your confirmed vehicle: 2026 Polo GTI, about R620,000, white, sunroof already included, no modifications. Driver, use and cover remain unanswered.',
    whatif: 'Fictional what-if: a younger driver, different use/security, optional benefits and R25,000 wheels. These are NOT your personal details or actual vehicle extras.',
  };
  document.querySelector('#scenario-note').textContent = notes[preset];
  document.querySelector('#scenario-note').classList.toggle('hypothetical-note', state.hypothetical);
  for (const button of document.querySelectorAll('[data-preset]')) {
    const active = button.dataset.preset === preset;
    button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active));
  }
  showStep(0);
  setFormError();
  invalidateReport();
  calculateEstimate(false);
}

form.addEventListener('input', () => { markEdited(); updateSunroofNote(); scheduleCalculation(); });
form.addEventListener('change', () => { markEdited(); updateSunroofNote(); scheduleCalculation(); });
form.addEventListener('submit', event => { event.preventDefault(); calculateEstimate(true); });
document.querySelector('#previous-step').addEventListener('click', () => showStep(state.step - 1));
document.querySelector('#next-step').addEventListener('click', () => showStep(state.step + 1));
document.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => showStep(steps.indexOf(button.dataset.step))));
document.querySelectorAll('[data-preset]').forEach(button => button.addEventListener('click', () => setPreset(button.dataset.preset)));
document.querySelector('#add-extra').addEventListener('click', () => {
  const extras = readExtras();
  if (extras.length >= 20) return;
  extras.push({ name: '', category: 'aftermarket', value: null, includedInVehicleValue: null });
  renderExtras(extras); markEdited(); scheduleCalculation();
  document.querySelector('.extra-row:last-child [data-extra-field="name"]').focus();
});
document.querySelector('#extras-list').addEventListener('click', event => {
  const remove = event.target.closest('[data-remove-extra]');
  if (!remove) return;
  const extras = readExtras();
  extras.splice(Number(remove.dataset.removeExtra), 1);
  renderExtras(extras); markEdited(); scheduleCalculation();
});

const rulesDialog = document.querySelector('#rules-dialog');
document.querySelector('#show-rules').addEventListener('click', () => rulesDialog.showModal());
document.querySelector('#close-rules').addEventListener('click', () => rulesDialog.close());
document.querySelector('#download-report').addEventListener('click', () => {
  if (!state.report || state.stale || state.calculating) return;
  const assessment = { ...state.report, scenario: { key: state.preset, hypothetical: state.hypothetical, note: document.querySelector('#scenario-note').textContent }, exportedAt: new Date().toISOString() };
  const url = URL.createObjectURL(new Blob([JSON.stringify(assessment, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url; link.download = `quote-lab-assessment-${new Date().toISOString().slice(0, 10)}.json`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
document.querySelector('#print-report').addEventListener('click', () => { if (state.report && !state.stale && !state.calculating) window.print(); });

// Printed assessments should include the audit trail, not only the open panels.
let detailsBeforePrint = [];
window.addEventListener('beforeprint', () => {
  detailsBeforePrint = [...document.querySelectorAll('#report-content details')].map(detail => ({ detail, open: detail.open }));
  for (const item of detailsBeforePrint) item.detail.open = true;
});
window.addEventListener('afterprint', () => {
  for (const item of detailsBeforePrint) item.detail.open = item.open;
  detailsBeforePrint = [];
});

async function startQuoteLab() {
  setProfile(knownVehicle());
  form.elements.year.max = String(new Date().getFullYear() + 1);
  document.querySelector('#show-rules').disabled = true;
  document.querySelector('#calculate-button').disabled = true;
  try {
    const [sessionResponse, configResponse] = await Promise.all([fetch('/api/session'), fetch('/api/insurance/config')]);
    if (!sessionResponse.ok || !configResponse.ok) throw new Error('Could not open the local demo. Start the Business Hub server and reload.');
    state.session = await sessionResponse.json(); state.config = await configResponse.json();
    renderRules(state.config);
    document.querySelector('#show-rules').disabled = false;
    document.querySelector('#calculate-button').disabled = false;
    await calculateEstimate(false);
  } catch (error) {
    setFormError(error.message);
    document.querySelector('#result-empty').innerHTML = '<h3>The demo could not load.</h3><p>Start the local server with run.ps1, then reload this page.</p>';
    document.querySelector('#result-status').textContent = 'Unavailable';
  }
}

startQuoteLab();
