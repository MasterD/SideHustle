import { icon } from './icons.js';

// This app uses ordinary functions and templates so small changes are easy to follow.
// The server owns the data and business rules. The browser only renders and sends input.
const state = {
  session: null,
  company: null,
  companyId: null,
  view: 'overview',
  data: {},
  leadSearch: '',
  leadStatus: '',
  bookingStatus: '',
  loadSequence: 0,
  switchingWorkspace: false,
  workspaceSequence: 0,
};

const views = {
  overview: { label: 'Overview', eyebrow: 'YOUR BUSINESS AT A GLANCE', title: 'Room to grow.', description: 'A clear view of your leads, your calendar, and your next move.' },
  leads: { label: 'Leads & customers', eyebrow: 'MAKE EVERY CONVERSATION COUNT', title: 'Good connections start here.', description: 'Follow an enquiry from first hello to a converted customer.' },
  bookings: { label: 'Bookings', eyebrow: 'A LITTLE MORE ORGANIZED', title: 'Your time, well spent.', description: 'Website requests arrive here. Confirm them when you are ready.' },
  content: { label: 'Content studio', eyebrow: 'ONE IDEA. MORE POSSIBILITIES.', title: 'Give your business a voice.', description: 'Write once. Publish to your local website and prepare your social posts.' },
  campaigns: { label: 'Campaigns', eyebrow: 'FROM IDEA TO ACTION', title: 'Make your next move.', description: 'Bring your offer, content, and lead attribution together.' },
  website: { label: 'Website', eyebrow: 'YOUR DIGITAL FRONT DOOR', title: 'Make a lovely first impression.', description: 'Edit your website, preview your draft, and publish it locally.' },
  settings: { label: 'Settings & services', eyebrow: 'BUILT AROUND YOUR BUSINESS', title: 'Make this space yours.', description: 'Your brand, your services, your hours. One reusable foundation.' },
};

const statusLabels = { new: 'New', contacted: 'Contacted', qualified: 'Qualified', won: 'Won', lost: 'Lost', requested: 'Requested', confirmed: 'Confirmed', completed: 'Completed', cancelled: 'Cancelled', draft: 'Draft', prepared: 'Prepared', published: 'Published locally', published_local: 'Published locally', demo_ready: 'Demo draft ready' };
const channels = ['website', 'facebook', 'instagram', 'linkedin'];
const channelNames = { website: 'Website', facebook: 'Facebook', instagram: 'Instagram', linkedin: 'LinkedIn' };
const pageContent = document.querySelector('#page-content');
const dialog = document.querySelector('#form-dialog');
let toastTimeout;

// Escape all company/customer input before placing it into an HTML template.
function escapeHtml(value = '') {
  return String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
}

function money(value = 0) {
  return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: state.company?.currency || 'ZAR', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(Number(value) || 0);
}

function dateLabel(value, includeTime = false) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('en-ZA', { timeZone: state.company?.timezone || 'Africa/Johannesburg', day: 'numeric', month: 'short', ...(includeTime ? { hour: '2-digit', minute: '2-digit' } : {}) }).format(date);
}

function timeLabel(value) {
  return new Intl.DateTimeFormat('en-ZA', { timeZone: state.company?.timezone || 'Africa/Johannesburg', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function initials(name = '') { return name.split(' ').filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase() || '?'; }
function badge(status) { return `<span class="status status-${escapeHtml(status)}">${escapeHtml(statusLabels[status] || status)}</span>`; }
function channelChips(selected = []) { return selected.map(channel => `<span class="channel-chip">${escapeHtml(channelNames[channel] || channel)}</span>`).join(''); }
function emptyState(title, description, action = '') { return `<div class="empty-state"><span class="empty-mark">${icon('leaf')}</span><h3>${title}</h3><p>${description}</p>${action}</div>`; }
function button(action, label, iconName = 'plus', className = 'button-primary', id = '') { return `<button class="button ${className}" data-action="${action}" ${id ? `data-id="${escapeHtml(id)}"` : ''}>${icon(iconName)}${label}</button>`; }

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(state.session?.csrfToken ? { 'X-CSRF-Token': state.session.csrfToken } : {}),
      ...options.headers,
    },
    ...(options.body ? { body: JSON.stringify(options.body) } : {}),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Something went wrong. Please try again.');
  return result;
}

function api(path, method = 'GET', body) {
  return request(`/api/companies/${encodeURIComponent(state.companyId)}${path}`, { method, ...(body !== undefined ? { body } : {}) });
}

function notify(message, isError = false) {
  const toast = document.querySelector('#toast');
  toast.textContent = message;
  toast.className = `toast visible ${isError ? 'toast-error' : ''}`;
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('visible'), isError ? 7000 : 4500);
}

function updateWorkspace() {
  document.querySelector('#company-select').innerHTML = state.session.companies.map(company => `<option value="${escapeHtml(company.id)}" ${company.id === state.companyId ? 'selected' : ''}>${escapeHtml(company.name)}</option>`).join('');
  document.querySelector('#sidebar-company').textContent = state.company.name;
  document.querySelector('.owner .avatar').textContent = initials(state.company.name);
  document.querySelector('#public-site-link').href = `/site/${encodeURIComponent(state.company.slug)}`;
  document.title = `Launchpad · ${state.company.name}`;
}

function setHeading() {
  const view = views[state.view];
  document.querySelector('#page-title').textContent = view.title;
  document.querySelector('#page-description').textContent = view.description;
  document.querySelector('#page-eyebrow').textContent = view.eyebrow;
  document.querySelector('#breadcrumb-title').textContent = view.label;
  document.querySelector('#navigation').innerHTML = Object.entries(views).map(([key, item]) => `<a href="#${key}" class="nav-item ${key === state.view ? 'active' : ''}" ${key === state.view ? 'aria-current="page"' : ''}>${icon(key)}<span>${item.label}</span>${key === 'campaigns' ? '<span class="nav-new">TRY IT</span>' : ''}</a>`).join('') + `<a href="/insurance" class="nav-item">${icon('insurance')}<span>Insurance Quote Lab</span></a>`;
  const actions = {
    overview: button('new-campaign', 'Create a campaign', 'plus'),
    leads: button('new-lead', 'Add a lead'),
    bookings: `<a class="button button-primary" href="/site/${encodeURIComponent(state.company.slug)}#services" target="_blank" rel="noopener">${icon('bookings')}Try the booking page ${icon('up')}</a>`,
    content: button('new-post', 'Write a post'),
    campaigns: button('new-campaign', 'New campaign'),
    website: `<a class="button button-secondary" href="/site/${encodeURIComponent(state.company.slug)}" target="_blank" rel="noopener">${icon('website')}Open your website ${icon('up')}</a>`,
    settings: button('export', 'Export workspace', 'download', 'button-secondary'),
  };
  document.querySelector('#page-actions').innerHTML = actions[state.view];
}

async function renderCurrentPage(showLoading = true) {
  if (state.switchingWorkspace) return;
  const sequence = ++state.loadSequence;
  setHeading();
  if (showLoading) pageContent.innerHTML = '<div class="loading-card"><span class="loading-dot"></span>Gathering your workspace…</div>';
  try {
    const routes = {
      overview: ['/overview'], leads: ['/leads'], bookings: ['/bookings', '/services'],
      content: ['/posts', '/deliveries'], campaigns: ['/campaigns'], website: ['/website'], settings: ['/settings', '/services'],
    };
    const results = await Promise.all(routes[state.view].map(path => api(path)));
    if (sequence !== state.loadSequence) return;
    state.data = Object.assign({}, ...results);
    if (state.view === 'settings') {
      // Settings is a company object, while the other API responses are named lists.
      state.data.company = results[0].company || results[0];
    }
    const renderers = { overview: renderOverview, leads: renderLeads, bookings: renderBookings, content: renderContent, campaigns: renderCampaigns, website: renderWebsite, settings: renderSettings };
    pageContent.innerHTML = renderers[state.view]();
    wirePageForms();
  } catch (error) {
    if (sequence !== state.loadSequence) return;
    pageContent.innerHTML = `<div class="error-card"><h3>We couldn’t load this page.</h3><p>${escapeHtml(error.message)}</p>${button('refresh', 'Try again', 'arrow', 'button-secondary')}</div>`;
  }
}

function renderOverview() {
  const { metrics = {}, leads = [], bookings = [], campaigns = [], activity = [], dailyLeads = [] } = state.data;
  const recentDays = dailyLeads.slice(-7);
  const pendingLeads = leads.filter(lead => ['new', 'contacted'].includes(lead.status));
  const upcoming = bookings.filter(booking => ['requested', 'confirmed'].includes(booking.status) && new Date(booking.startAt) > new Date()).sort((a, b) => a.startAt.localeCompare(b.startAt)).slice(0, 4);
  const cards = [
    { label: 'NEW LEADS', value: metrics.newLeads || 0, note: 'Ready for a first conversation', icon: 'leads', color: 'lavender' },
    { label: 'CONFIRMED BOOKINGS', value: metrics.confirmedBookings || 0, note: 'Appointments on your calendar', icon: 'bookings', color: 'peach' },
    { label: 'OPEN PIPELINE', value: money(metrics.pipelineValue), note: 'Potential value · not revenue', icon: 'campaigns', color: 'sky' },
    { label: 'CONVERTED VALUE', value: money(metrics.convertedValue), note: 'Won leads · not collected payments', icon: 'check', color: 'blue' },
  ];
  return `<section class="growth-banner">
    <div><span class="banner-kicker">LET’S GET YOU OUT THERE</span>
      <h2>One workspace.<br>A whole new reach.</h2>
      <p>Turn your next offer into a website update,<br>social drafts, and a trackable campaign.</p>
      ${button('new-campaign', 'Build your next campaign', 'arrow', 'button-dark')}
    </div>
    <div class="banner-art" aria-hidden="true">
      <div class="campaign-sheet-back"></div>
      <div class="campaign-sheet">
        <div class="sheet-top"><span class="sheet-symbol">↗</span><span>YOUR NEXT CAMPAIGN</span><i></i></div>
        <div class="sheet-title">A fresh idea.<br>A wider audience.</div>
        <div class="sheet-rule"></div><div class="sheet-rule sheet-rule-short"></div>
        <div class="sheet-channels"><span>${icon('website')}</span><span>${icon('content')}</span><span>${icon('leads')}</span></div>
        <div class="sheet-progress"><i></i></div>
      </div>
      <span class="art-tag tag-one">${icon('check')}Content prepared</span>
      <span class="art-tag tag-two">${icon('arrow')}Ready for your next move</span>
    </div>
    <span class="banner-count">LOCAL CAMPAIGN WORKFLOW</span>
  </section>
    <div class="section-title"><h2>Your business, at a glance</h2><span class="subtle">All-time workspace totals</span></div>
    <section class="metrics-grid">${cards.map(card => `<article class="metric-card"><div class="metric-top"><span>${card.label}</span><span class="metric-icon ${card.color}">${icon(card.icon)}</span></div><strong>${card.value}</strong><p>${card.note}</p></article>`).join('')}</section>
    <div class="dashboard-grid"><section class="panel lead-chart-panel"><div class="panel-heading"><div><h2>Conversations taking root</h2><p>New leads recorded over the last 7 days</p></div><span class="tiny-pill">7 DAYS</span></div>${renderLeadChart(recentDays)}<div class="chart-footer"><span><i class="chart-key"></i> Enquiries & booking leads</span><a href="#leads">See all leads ${icon('arrow')}</a></div></section>
    <section class="panel"><div class="panel-heading"><div><h2>Coming up</h2><p>Your next booking requests</p></div><a class="text-link" href="#bookings">View all ${icon('arrow')}</a></div>${upcoming.length ? `<div class="appointment-list">${upcoming.map(booking => `<div class="appointment"><div class="date-block"><strong>${new Date(booking.startAt).toLocaleDateString('en-ZA', { day: 'numeric', timeZone: state.company.timezone })}</strong><span>${new Date(booking.startAt).toLocaleDateString('en-ZA', { month: 'short', timeZone: state.company.timezone })}</span></div><div class="appointment-info"><strong>${escapeHtml(booking.serviceName)}</strong><span>${escapeHtml(booking.name)} · ${timeLabel(booking.startAt)}</span></div>${badge(booking.status)}</div>`).join('')}</div>` : emptyState('A little breathing room.', 'Booking requests from your website will appear here.')}</section></div>
    <div class="dashboard-grid lower-grid"><section class="panel"><div class="panel-heading"><div><h2>A hello worth following up</h2><p>Keep the conversation moving</p></div><a class="text-link" href="#leads">Your pipeline ${icon('arrow')}</a></div>${pendingLeads.length ? pendingLeads.slice(0, 4).map(lead => `<div class="follow-up-row"><span class="avatar avatar-soft">${escapeHtml(initials(lead.name))}</span><div><strong>${escapeHtml(lead.name)}</strong><small>${escapeHtml(lead.source || 'Website enquiry')}</small></div>${button('edit-lead', 'Follow up', 'arrow', 'button-small button-quiet', lead.id)}</div>`).join('') : emptyState('All caught up.', 'New conversations will show up here.')}</section>
    <section class="panel activity-panel"><div class="panel-heading"><div><h2>Behind the scenes</h2><p>Your latest workspace activity</p></div><span class="activity-dot"></span></div><div class="activity-list">${activity.length ? activity.slice(0, 5).map(item => `<div class="activity-item"><span class="activity-bullet"></span><div><p>${escapeHtml(item.message)}</p><small>${dateLabel(item.createdAt, true)}</small></div></div>`).join('') : '<p class="subtle">Your saved changes will appear here.</p>'}</div></section></div>
    <div class="insight-note">${icon('leaf')}<span>${campaigns.length} recent campaign${campaigns.length === 1 ? '' : 's'} · Estimated conversion incentive: <strong>${money(metrics.estimatedCommission)}</strong> based on saved lead values and rates.</span><a href="#settings">Manage your workspace ${icon('arrow')}</a></div>`;
}

function renderLeadChart(days) {
  const maximum = Math.max(1, ...days.map(day => day.count));
  return `<div class="bar-chart" role="img" aria-label="${escapeHtml(days.map(day => `${day.date}: ${day.count} leads`).join(', ') || 'No leads recorded')} "><div class="chart-grid"><span>${maximum}</span><span>${Math.round(maximum / 2)}</span><span>0</span></div><div class="chart-bars">${days.map(day => `<div class="bar-column"><span class="bar-value">${day.count}</span><div class="bar" style="height:${Math.max(2, day.count / maximum * 130)}px" title="${escapeHtml(day.date)}: ${day.count} leads"></div><span class="bar-label">${new Date(`${day.date}T12:00:00`).toLocaleDateString('en-ZA', { weekday: 'short' })}</span></div>`).join('')}</div></div>`;
}

function filteredLeads() {
  const search = state.leadSearch.toLowerCase();
  return (state.data.leads || []).filter(lead => (!state.leadStatus || lead.status === state.leadStatus) && [lead.name, lead.email, lead.phone, lead.source].some(value => String(value || '').toLowerCase().includes(search)));
}

function renderLeadRows() {
  const leads = filteredLeads();
  return leads.length ? leads.map(lead => `<tr><td><div class="person-cell"><span class="avatar avatar-soft">${escapeHtml(initials(lead.name))}</span><div><strong>${escapeHtml(lead.name)}</strong><small>${escapeHtml(lead.email)}</small></div></div></td><td><span class="source-label">${escapeHtml(lead.source || 'Manual')}</span><small class="cell-small">${dateLabel(lead.createdAt)}</small></td><td><select class="status-select status-${escapeHtml(lead.status)}" data-lead-status="${escapeHtml(lead.id)}" aria-label="Status for ${escapeHtml(lead.name)}">${['new', 'contacted', 'qualified', 'won', 'lost'].map(status => `<option value="${status}" ${status === lead.status ? 'selected' : ''}>${statusLabels[status]}</option>`).join('')}</select></td><td><strong>${money(lead.value)}</strong><small class="cell-small">${Number(lead.commissionRate || 0)}% incentive</small></td><td>${button('edit-lead', 'Details', 'edit', 'button-small button-quiet', lead.id)}</td></tr>`).join('') : '<tr><td colspan="5">' + emptyState('No matching conversations.', 'Add a lead or try a different search.') + '</td></tr>';
}

function renderLeads() {
  const counts = ['new', 'contacted', 'qualified', 'won', 'lost'].map(status => ({ status, count: (state.data.leads || []).filter(lead => lead.status === status).length }));
  return `<div class="pipeline-strip">${counts.map(item => `<button class="pipeline-stage ${state.leadStatus === item.status ? 'selected' : ''}" data-action="filter-leads" data-status="${item.status}">
    <span class="stage-dot stage-${item.status}">
    </span>
    <span>${statusLabels[item.status]}</span>
    <strong>${item.count}</strong>
    </button>`).join('')}</div>
    <section class="panel table-panel">
    <div class="table-toolbar">
    <label class="search-field">
    <span aria-hidden="true">⌕</span>
    <input id="lead-search" type="search" placeholder="Search names, email, or source…" value="${escapeHtml(state.leadSearch)}" aria-label="Search leads">
    </label>
    <select id="lead-filter" aria-label="Filter lead status">
    <option value="">All stages</option>${counts.map(item => `<option value="${item.status}" ${state.leadStatus === item.status ? 'selected' : ''}>${statusLabels[item.status]}</option>`).join('')}</select>
    <span class="subtle">${state.data.leads.length} total conversations</span>
    </div>
    <div class="table-scroll">
    <table>
    <thead>
    <tr>
    <th>PERSON</th>
    <th>SOURCE / ADDED</th>
    <th>STAGE</th>
    <th>POTENTIAL VALUE</th>
    <th>
    </th>
    </tr>
    </thead>
    <tbody id="lead-rows">${renderLeadRows()}</tbody>
    </table>
    </div>
    </section>
    <div class="help-note">${icon('leads')}<p>Mark a lead <strong>Won</strong> when it converts. Value and incentive estimates come from your entries; they do not record payments or trigger payouts.</p>
    </div>`;
}

function renderBookings() {
  const all = state.data.bookings || [];
  const bookings = all.filter(booking => !state.bookingStatus || booking.status === state.bookingStatus).sort((a, b) => a.startAt.localeCompare(b.startAt));
  return `<div class="booking-summary">
    <div>${icon('bookings')}<strong>${all.filter(item => item.status === 'requested').length}</strong>
    <span>awaiting confirmation</span>
    </div>
    <div>${icon('check')}<strong>${all.filter(item => item.status === 'confirmed').length}</strong>
    <span>confirmed</span>
    </div>
    <div class="booking-hours">${icon('clock')}<span>${escapeHtml(state.company.openingTime)}–${escapeHtml(state.company.closingTime)} · ${escapeHtml(state.company.timezone)}</span>
    </div>
    </div>
    <div class="tabs" role="group" aria-label="Filter bookings">${[['', 'All bookings'], ['requested', 'Requested'], ['confirmed', 'Confirmed'], ['completed', 'Completed'], ['cancelled', 'Cancelled']].map(([status, label]) => `<button class="tab ${state.bookingStatus === status ? 'active' : ''}" data-action="filter-bookings" data-status="${status}">${label}</button>`).join('')}</div>
    <section class="panel booking-panel">${bookings.length ? bookings.map(booking => `<article class="booking-row">
    <div class="booking-time">
    <strong>${timeLabel(booking.startAt)}</strong>
    <span>${dateLabel(booking.startAt)}</span>
    </div>
    <div class="booking-main">
    <h3>${escapeHtml(booking.serviceName)}</h3>
    <p>${escapeHtml(booking.name)} <span>·</span> ${escapeHtml(booking.email)}</p>${booking.message ? `<small>${escapeHtml(booking.message)}</small>` : ''}</div>
    <div class="booking-controls">
    <select class="status-select status-${escapeHtml(booking.status)}" data-booking-status="${escapeHtml(booking.id)}" aria-label="Status for ${escapeHtml(booking.name)} booking">${['requested', 'confirmed', 'completed', 'cancelled'].map(status => `<option value="${status}" ${booking.status === status ? 'selected' : ''}>${statusLabels[status]}</option>`).join('')}</select>
    <small>${Math.round((new Date(booking.endAt) - new Date(booking.startAt)) / 60000)} min</small>
    </div>
    </article>`).join('') : emptyState('Your calendar is ready.', 'Customers can request a time through your website.')} </section>
    <div class="help-note">${icon('clock')}<p>Requested and confirmed bookings reserve the time slot. Cancelling releases it. Your opening hours and service durations are managed in <a href="#settings">Settings & services</a>.</p>
    </div>`;
}

function renderContent() {
  const { posts = [], deliveries = [] } = state.data;
  return `<div class="integration-strip">
    <div class="integration-heading">
    <span class="round-icon">${icon('content')}</span>
    <div>
    <strong>Your channels</strong>
    <small>A shared message, tailored to each destination.</small>
    </div>
    </div>
    <div class="integration-channels">
    <span>
    <i class="connection-dot">
    </i>Website <small>Local publishing</small>
    </span>${['facebook', 'instagram', 'linkedin'].map(channel => `<span>
    <i class="connection-dot demo-dot">
    </i>${channelNames[channel]}<small>Demo preparation</small>
    </span>`).join('')}</div>
    </div>
    <div class="section-title">
    <h2>Your story, in the making</h2>
    <span class="subtle">${posts.length} saved posts</span>
    </div>
    <div class="post-grid">${posts.length ? posts.map(post => `<article class="panel post-card">
    <div class="card-top">${badge(post.status)}<span class="subtle">${dateLabel(post.createdAt)}</span>
    </div>
    <h3>${escapeHtml(post.title)}</h3>
    <p class="post-body">${escapeHtml(post.body)}</p>
    <div class="channel-chips">${channelChips(post.channels)}</div>
    <div class="card-actions">${button('edit-post', 'Edit', 'edit', 'button-small button-quiet', post.id)}${button('publish-post', 'Prepare & publish', 'arrow', 'button-small button-secondary', post.id)}</div>
    </article>`).join('') : `<section class="panel full-width">${emptyState('Start with something worth sharing.', 'Write an update, a useful tip, or a new offer.', button('new-post', 'Write your first post'))}</section>`}</div>
    <section class="panel delivery-panel">
    <div class="panel-heading">
    <div>
    <h2>Publishing log</h2>
    <p>Website updates and prepared social drafts</p>
    </div>
    </div>${deliveries.length ? `<div class="table-scroll">
    <table>
    <thead>
    <tr>
    <th>CONTENT</th>
    <th>DESTINATION</th>
    <th>RESULT</th>
    <th>DATE</th>
    </tr>
    </thead>
    <tbody>${deliveries.slice(0, 20).map(delivery => `<tr>
    <td>${escapeHtml(delivery.title)}</td>
    <td>${escapeHtml(channelNames[delivery.channel] || delivery.channel)}</td>
    <td>${badge(delivery.status)}</td>
    <td>${dateLabel(delivery.createdAt, true)}</td>
    </tr>`).join('')}</tbody>
    </table>
    </div>` : '<p class="panel-empty">Your first prepared post will create a delivery record here.</p>'}</section>
    <div class="help-note">${icon('content')}<p>Social accounts are not connected. This demo saves drafts for each selected platform. Publishing to your local website works now; real social delivery needs account connections and platform-specific adapters.</p>
    </div>`;
}

function renderCampaigns() {
  const campaigns = state.data.campaigns || [];
  return `<div class="campaign-flow">
    <div>
    <span>01</span>
    <strong>Define your offer</strong>
    <small>A clear reason to get in touch</small>
    </div>${icon('arrow')}<div>
    <span>02</span>
    <strong>Prepare your channels</strong>
    <small>Website + social content</small>
    </div>${icon('arrow')}<div>
    <span>03</span>
    <strong>Follow the connection</strong>
    <small>Attributed leads and bookings</small>
    </div>
    </div>
    <div class="section-title">
    <h2>Your next opportunities</h2>
    <span class="subtle">No ad spend is connected</span>
    </div>
    <div class="campaign-grid">${campaigns.length ? campaigns.map(campaign => `<article class="panel campaign-card">
    <div class="card-top">
    <span class="campaign-symbol">${icon('campaigns')}</span>${badge(campaign.status)}</div>
    <span class="eyebrow">${escapeHtml(campaign.objective)} CAMPAIGN</span>
    <h3>${escapeHtml(campaign.name)}</h3>
    <p>${escapeHtml(campaign.offer)}</p>
    <div class="channel-chips">${channelChips(campaign.channels)}</div>
    <div class="campaign-budget">
    <div>
    <small>PLANNED BUDGET</small>
    <strong>${money(campaign.plannedBudget)}</strong>
    </div>
    <div>
    <small>ACTUAL SPEND</small>
    <strong>${money(0)}</strong>
    </div>
    </div>
    <div class="campaign-source">
    <span>Tracked landing page</span>
    <a href="/site/${encodeURIComponent(state.company.slug)}?campaign=${encodeURIComponent(campaign.sourceCode)}" target="_blank" rel="noopener">${escapeHtml(campaign.sourceCode)} ${icon('up')}</a>
    </div>${button('run-campaign', campaign.status === 'prepared' ? 'View / run again' : 'Run demo campaign', 'arrow', 'button-primary full-width', campaign.id)}</article>`).join('') : `<section class="panel full-width">${emptyState('An idea is a good place to start.', 'Create an offer and choose where you want it to appear.', button('new-campaign', 'Create your first campaign'))}</section>`}</div>
    <div class="help-note">${icon('campaigns')}<p>
    <strong>What “Run demo campaign” does:</strong> prepares a reusable post, publishes it to the local website when selected, and records social drafts. Re-running does not duplicate the campaign. It does not buy ads, send messages, or invent leads.</p>
    </div>`;
}

function websitePreview(website) {
  return `<div class="website-mini"><div class="mini-browser"><i></i><i></i><i></i><span>${escapeHtml(state.company.slug)} · local preview</span></div><div class="mini-site"><div class="mini-nav"><strong>${escapeHtml(state.company.name)}</strong><span>Our story &nbsp; Services &nbsp; Journal</span></div><div class="mini-hero"><small>MAKE SPACE FOR SOMETHING GOOD</small><h2>${escapeHtml(website.headline || state.company.tagline)}</h2><p>${escapeHtml(website.subheadline)}</p><span class="mini-cta">${escapeHtml(website.ctaLabel || 'Book a visit')} ↗</span><div class="mini-plant" aria-hidden="true">${icon('leaf')}</div></div><div class="mini-about"><small>ROOTED IN GOOD THINGS</small><p>${escapeHtml(website.about)}</p></div>${website.announcement ? `<div class="mini-announcement">${escapeHtml(website.announcement)}</div>` : ''}</div></div>`;
}

function renderWebsite() {
  const { draft = {}, published = {} } = state.data;
  const hasChanges = ['headline', 'subheadline', 'about', 'ctaLabel', 'announcement'].some(key => draft[key] !== published[key]);
  return `<div class="website-editor-grid">
    <section class="panel editor-panel">
    <div class="panel-heading">
    <div>
    <h2>A few words can change everything.</h2>
    <p>Edit your draft, then publish when it feels right.</p>
    </div>
    </div>
    <form id="website-form">
    <label>Headline<input name="headline" value="${escapeHtml(draft.headline)}" maxlength="200" required>
    </label>
    <label>Introduction<textarea name="subheadline" rows="3" maxlength="500" required>${escapeHtml(draft.subheadline)}</textarea>
    </label>
    <label>Your story<textarea name="about" rows="5" maxlength="5000" required>${escapeHtml(draft.about)}</textarea>
    </label>
    <label>Booking button text<input name="ctaLabel" value="${escapeHtml(draft.ctaLabel)}" maxlength="80" required>
    </label>
    <label>Announcement <span class="optional">optional</span>
    <textarea name="announcement" rows="2" maxlength="1000" placeholder="A new workshop, seasonal offer, or a little news…">${escapeHtml(draft.announcement)}</textarea>
    </label>
    <div class="form-error" role="alert">
    </div>
    <div class="form-actions">
    <button class="button button-secondary" type="submit" name="intent" value="save">Save draft</button>
    <button class="button button-primary" type="submit" name="intent" value="publish">${icon('website')}Publish locally</button>
    </div>
    </form>
    </section>
    <div class="website-preview-column">
    <div class="preview-header">
    <span class="tiny-pill">DRAFT PREVIEW</span>
    <span id="website-draft-status" class="subtle">${hasChanges ? 'Draft has unpublished changes' : 'Draft matches published version'}</span>
    </div>
    <div id="website-preview">${websitePreview(draft)}</div>
    <div class="preview-footnote">${icon('check')}<p>The live local website uses your last published version. Saving a draft keeps it private until you publish.</p>
    </div>
    <a class="button button-secondary full-width" href="/site/${encodeURIComponent(state.company.slug)}" target="_blank" rel="noopener">Open published website ${icon('up')}</a>
    </div>
    </div>`;
}

function renderSettings() {
  const company = state.data.company || state.company;
  const services = state.data.services || [];
  const weekdays = [[1, 'Mon'], [2, 'Tue'], [3, 'Wed'], [4, 'Thu'], [5, 'Fri'], [6, 'Sat'], [7, 'Sun']];
  return `<div class="settings-grid">
    <section class="panel editor-panel">
    <div class="panel-heading">
    <div>
    <h2>The essentials</h2>
    <p>Company details shared across the website and dashboard.</p>
    </div>
    </div>
    <form id="settings-form">
    <div class="form-two">
    <label>Company name<input name="name" required maxlength="120" value="${escapeHtml(company.name)}">
    </label>
    <label>Brand accent<input name="accentColor" type="color" value="${escapeHtml(company.accentColor || '#315fe7')}">
    </label>
    </div>
    <label>Tagline<input name="tagline" maxlength="200" required value="${escapeHtml(company.tagline)}">
    </label>
    <label>Business description<textarea name="description" rows="3" maxlength="5000">${escapeHtml(company.description)}</textarea>
    </label>
    <div class="form-two">
    <label>Contact email<input type="email" name="email" value="${escapeHtml(company.email)}" maxlength="254">
    </label>
    <label>Phone<input name="phone" value="${escapeHtml(company.phone)}" maxlength="40">
    </label>
    </div>
    <label>Address / service area<input name="address" value="${escapeHtml(company.address)}" maxlength="300">
    </label>
    <div class="form-two">
    <label>Business timezone<input name="timezone" value="${escapeHtml(company.timezone)}" required placeholder="Africa/Johannesburg">
    </label>
    <label>Currency<select name="currency">${['ZAR', 'USD', 'EUR', 'GBP'].map(currency => `<option ${currency === company.currency ? 'selected' : ''}>${currency}</option>`).join('')}</select>
    </label>
    </div>
    <label>Default conversion incentive (%)<input name="commissionRate" type="number" min="0" max="100" step="0.1" value="${Number(company.commissionRate || 0)}">
    <small>Used for new manual leads and website enquiries. Existing lead rates keep their saved values.</small>
    </label>
    <h3 class="form-section-title">Booking hours</h3>
    <div class="day-checkboxes">${weekdays.map(([day, name]) => `<label>
    <input type="checkbox" name="bookingDays" value="${day}" ${(company.bookingDays || []).includes(day) ? 'checked' : ''}>
    <span>${name}</span>
    </label>`).join('')}</div>
    <div class="form-two">
    <label>Opens at<input type="time" name="openingTime" value="${escapeHtml(company.openingTime)}" required>
    </label>
    <label>Closes at<input type="time" name="closingTime" value="${escapeHtml(company.closingTime)}" required>
    </label>
    </div>
    <div class="form-error" role="alert">
    </div>
    <div class="form-actions">
    <button class="button button-primary" type="submit">Save workspace settings ${icon('check')}</button>
    </div>
    </form>
    </section>
    <div>
    <section class="panel services-panel">
    <div class="panel-heading">
    <div>
    <h2>Your services</h2>
    <p>The choices on your booking page.</p>
    </div>${button('new-service', 'Add', 'plus', 'button-small button-secondary')}</div>${services.length ? services.map(service => `<article class="service-row">
    <span class="service-icon">${icon('leaf')}</span>
    <div>
    <strong>${escapeHtml(service.name)}</strong>
    <small>${service.durationMinutes} min · ${money(service.price)} · ${service.active ? 'Active' : 'Hidden'}</small>
    <p>${escapeHtml(service.description)}</p>
    </div>
    <button class="icon-button" data-action="edit-service" data-id="${escapeHtml(service.id)}" aria-label="Edit ${escapeHtml(service.name)}">${icon('edit')}</button>
    </article>`).join('') : emptyState('Add your first service.', 'A service needs a duration before it can be booked.')}</section>
    <section class="workspace-info">
    <span class="eyebrow">READY FOR ANOTHER BUSINESS</span>
    <h3>A new company. The same foundation.</h3>
    <p>Each workspace has its own website, services, leads, bookings, and content.</p>${button('new-company', 'Add a workspace', 'plus', 'button-secondary')}<small>Local workspaces share access on this computer. Hosted client accounts need proper sign-in and access controls.</small>
    </section>
    </div>
    </div>`;
}

// Forms are wired after rendering. Validation messages stay next to the form.
function wirePageForms() {
  const search = document.querySelector('#lead-search');
  if (search) search.addEventListener('input', () => { state.leadSearch = search.value; document.querySelector('#lead-rows').innerHTML = renderLeadRows(); });
  const filter = document.querySelector('#lead-filter');
  if (filter) filter.addEventListener('change', () => { state.leadStatus = filter.value; pageContent.innerHTML = renderLeads(); wirePageForms(); });
  const websiteForm = document.querySelector('#website-form');
  if (websiteForm) {
    websiteForm.addEventListener('input', () => {
      const draft = Object.fromEntries(new FormData(websiteForm));
      document.querySelector('#website-preview').innerHTML = websitePreview(draft);
      document.querySelector('#website-draft-status').textContent = 'Unsaved changes';
    });
    websiteForm.addEventListener('submit', event => submitForm(event, async form => {
      const values = Object.fromEntries(new FormData(form));
      await api('/website', 'PATCH', values);
      if (event.submitter?.value === 'publish') await api('/website/publish', 'POST', {});
      notify(event.submitter?.value === 'publish' ? 'Your local website is updated.' : 'Draft saved. Publish when you’re ready.');
      await renderCurrentPage(false);
    }));
  }
  const settingsForm = document.querySelector('#settings-form');
  if (settingsForm) settingsForm.addEventListener('submit', event => submitForm(event, async form => {
    const data = new FormData(form);
    const values = Object.fromEntries(data);
    values.bookingDays = data.getAll('bookingDays').map(Number);
    values.commissionRate = Number(values.commissionRate);
    const result = await api('/settings', 'PATCH', values);
    state.company = result.company || result;
    state.session = await request('/api/session');
    updateWorkspace();
    notify('Workspace settings saved.');
    await renderCurrentPage(false);
  }));
}

async function submitForm(event, operation) {
  event.preventDefault();
  const form = event.currentTarget;
  const errorBox = form.querySelector('.form-error');
  const submitButtons = [...form.querySelectorAll('button[type="submit"]')];
  if (errorBox) errorBox.textContent = '';
  submitButtons.forEach(button => { button.disabled = true; });
  document.querySelector('#company-select').disabled = true;
  try { await operation(form); }
  catch (error) { if (errorBox) errorBox.textContent = error.message; else notify(error.message, true); }
  finally {
    submitButtons.forEach(button => { button.disabled = false; });
    if (!state.switchingWorkspace) document.querySelector('#company-select').disabled = false;
  }
}

function openForm(title, html, operation, eyebrow = 'WORKSPACE') {
  document.querySelector('#dialog-title').textContent = title;
  document.querySelector('#dialog-eyebrow').textContent = eyebrow;
  document.querySelector('#dialog-body').innerHTML = `<form id="modal-form">${html}<div class="form-error" role="alert"></div><div class="form-actions"><button type="button" class="button button-quiet" data-action="close-dialog">Cancel</button><button type="submit" class="button button-primary">Save ${icon('check')}</button></div></form>`;
  document.querySelector('#modal-form').addEventListener('submit', event => submitForm(event, async form => {
    await operation(new FormData(form));
    dialog.close();
    await renderCurrentPage(false);
  }));
  dialog.showModal();
}

function channelFields(selected = ['website', 'facebook', 'instagram']) {
  return `<fieldset class="channel-fieldset"><legend>Where should it appear?</legend><div class="channel-checkboxes">${channels.map(channel => `<label><input type="checkbox" name="channels" value="${channel}" ${selected.includes(channel) ? 'checked' : ''}><span>${channelNames[channel]}<small>${channel === 'website' ? 'Local publishing' : 'Demo draft'}</small></span></label>`).join('')}</div></fieldset>`;
}

function openLeadForm(lead = {}) {
  openForm(lead.id ? 'Keep the conversation moving.' : 'A new connection.', `<div class="form-two">
    <label>Name<input name="name" value="${escapeHtml(lead.name)}" maxlength="120" required ${lead.id ? 'readonly' : ''}>
    </label>
    <label>Email<input name="email" type="email" maxlength="254" value="${escapeHtml(lead.email)}" ${lead.id ? 'readonly' : ''}>
    </label>
    </div>
    <div class="form-two">
    <label>Phone<input name="phone" maxlength="40" value="${escapeHtml(lead.phone)}" ${lead.id ? 'readonly' : ''}>
    </label>
    <label>Source<input name="source" maxlength="120" value="${escapeHtml(lead.source || 'Manual')}" ${lead.id ? 'readonly' : ''}>
    </label>
    </div>
    <label>Stage<select name="status">${['new', 'contacted', 'qualified', 'won', 'lost'].map(status => `<option value="${status}" ${status === (lead.status || 'new') ? 'selected' : ''}>${statusLabels[status]}</option>`).join('')}</select>
    </label>
    <div class="form-two">
    <label>Potential value (${escapeHtml(state.company.currency)})<input type="number" name="value" min="0" max="100000000" step="0.01" value="${Number(lead.value || 0)}" required>
    </label>
    <label>Conversion incentive (%)<input type="number" name="commissionRate" min="0" max="100" step="0.1" value="${Number(lead.commissionRate ?? state.company.commissionRate ?? 0)}" required>
    </label>
    </div>${lead.message ? `<div class="original-message">
    <small>ORIGINAL ENQUIRY</small>
    <p>${escapeHtml(lead.message)}</p>
    </div>` : ''}<label>${lead.id ? 'Follow-up notes' : 'Message / notes'}<textarea name="${lead.id ? 'notes' : 'message'}" maxlength="5000" rows="4">${escapeHtml(lead.notes || (!lead.id ? lead.message : ''))}</textarea>
    </label>`, async data => {
    const values = Object.fromEntries(data);
    values.value = Number(values.value);
    values.commissionRate = Number(values.commissionRate);
    await api(lead.id ? `/leads/${encodeURIComponent(lead.id)}` : '/leads', lead.id ? 'PATCH' : 'POST', values);
    notify(lead.id ? 'Lead updated.' : 'New lead saved.');
  }, 'LEADS & CUSTOMERS');
}

function openPostForm(post = {}) {
  openForm(post.id ? 'A little polish for your post.' : 'What would you like to share?', `<label>Post title<input name="title" maxlength="200" required value="${escapeHtml(post.title)}" placeholder="A new workshop. A fresh idea."></label><label>Your message<textarea name="body" maxlength="5000" rows="7" required placeholder="Tell your story…">${escapeHtml(post.body)}</textarea></label>${channelFields(post.channels)}<div class="inline-note">This saves a draft. Any previously published website version stays live until you prepare & publish again.</div>`, async data => {
    const values = Object.fromEntries(data);
    values.channels = data.getAll('channels');
    if (!values.channels.length) throw new Error('Choose at least one destination.');
    await api(post.id ? `/posts/${encodeURIComponent(post.id)}` : '/posts', post.id ? 'PATCH' : 'POST', values);
    notify('Post draft saved.');
  }, 'CONTENT STUDIO');
}

function openCampaignForm() {
  openForm('Give your next idea a launchpad.', `<label>Campaign name<input name="name" maxlength="200" required placeholder="The spring refresh"></label><div class="form-two"><label>Your goal<select name="objective"><option value="leads">More enquiries</option><option value="bookings">More bookings</option><option value="awareness">Brand awareness</option></select></label><label>Planned budget (${escapeHtml(state.company.currency)})<input name="plannedBudget" type="number" min="0" max="100000000" step="0.01" value="0" required><small>Planning only. Nothing will be charged.</small></label></div><label>Your offer<textarea name="offer" rows="4" maxlength="5000" required placeholder="What is the offer, who is it for, and why should they get in touch?"></textarea></label>${channelFields()}<div class="inline-note">Running prepares content and a source link. Website publication is local; social posts stay in the demo queue.</div>`, async data => {
    const values = Object.fromEntries(data);
    values.channels = data.getAll('channels');
    values.plannedBudget = Number(values.plannedBudget);
    if (!values.channels.length) throw new Error('Choose at least one destination.');
    await api('/campaigns', 'POST', values);
    notify('Campaign saved. Run it from the Campaigns page.');
    state.view = 'campaigns';
    history.replaceState(null, '', '#campaigns');
  }, 'CAMPAIGNS');
}

function openServiceForm(service = {}) {
  openForm(service.id ? 'Fine-tune your service.' : 'Make room for a new service.', `<label>Service name<input name="name" maxlength="120" required value="${escapeHtml(service.name)}"></label><label>Description<textarea name="description" rows="3" maxlength="2000">${escapeHtml(service.description)}</textarea></label><div class="form-two"><label>Duration in minutes<input name="durationMinutes" type="number" min="15" max="480" step="15" required value="${Number(service.durationMinutes || 60)}"></label><label>Price (${escapeHtml(state.company.currency)})<input name="price" type="number" min="0" max="100000000" step="0.01" required value="${Number(service.price || 0)}"></label></div><label class="checkbox-line"><input name="active" type="checkbox" ${service.active !== false ? 'checked' : ''}>Available on the website</label><div class="inline-note">Changes apply to new bookings. Existing bookings keep the duration they were booked with.</div>`, async data => {
    const values = Object.fromEntries(data);
    values.durationMinutes = Number(values.durationMinutes);
    values.price = Number(values.price);
    values.active = data.has('active');
    await api(service.id ? `/services/${encodeURIComponent(service.id)}` : '/services', service.id ? 'PATCH' : 'POST', values);
    notify('Service saved.');
  }, 'SERVICES');
}

function openCompanyForm() {
  openForm('A fresh workspace.', `<label>Company name<input name="name" maxlength="120" required placeholder="Your next demo company"></label><label>Website address name<input name="slug" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" minlength="3" maxlength="60" required placeholder="your-demo-company"><small>Lowercase letters, numbers, and hyphens. This becomes /site/your-demo-company and stays fixed.</small></label><div class="inline-note">The new workspace starts with its own website draft and service. Your current company’s records stay in its workspace.</div>`, async data => {
    const result = await request('/api/companies', { method: 'POST', body: Object.fromEntries(data) });
    state.company = result.company || result;
    state.companyId = state.company.id;
    state.session = await request('/api/session');
    state.data = {};
    state.leadSearch = ''; state.leadStatus = ''; state.bookingStatus = '';
    state.view = 'settings';
    history.replaceState(null, '', '#settings');
    updateWorkspace();
    notify('Your new workspace is ready.');
  }, 'NEW WORKSPACE');
}

async function handleAction(event) {
  const element = event.target.closest('[data-action]');
  if (!element) return;
  if (state.switchingWorkspace) return;
  const { action, id, status } = element.dataset;
  if (action === 'close-dialog') return dialog.close();
  if (action === 'new-lead') return openLeadForm();
  if (action === 'edit-lead') {
    let lead = (state.data.leads || []).find(item => item.id === id);
    if (!lead) lead = (await api('/leads')).leads.find(item => item.id === id);
    return openLeadForm(lead);
  }
  if (action === 'new-post') return openPostForm();
  if (action === 'edit-post') return openPostForm(state.data.posts.find(item => item.id === id));
  if (action === 'new-campaign') return openCampaignForm();
  if (action === 'new-service') return openServiceForm();
  if (action === 'edit-service') return openServiceForm(state.data.services.find(item => item.id === id));
  if (action === 'new-company') return openCompanyForm();
  if (action === 'filter-leads') { state.leadStatus = state.leadStatus === status ? '' : status; pageContent.innerHTML = renderLeads(); return wirePageForms(); }
  if (action === 'filter-bookings') { state.bookingStatus = status; pageContent.innerHTML = renderBookings(); return; }
  element.disabled = true;
  document.querySelector('#company-select').disabled = true;
  try {
    if (action === 'refresh') await renderCurrentPage();
    if (action === 'publish-post') {
      const result = await api(`/posts/${encodeURIComponent(id)}/publish`, 'POST', {});
      const local = (result.deliveries || []).some(delivery => delivery.channel === 'website');
      notify(local ? 'Published on your local website. Selected social drafts are prepared.' : 'Selected social drafts are prepared.');
      await renderCurrentPage(false);
    }
    if (action === 'run-campaign') {
      const result = await api(`/campaigns/${encodeURIComponent(id)}/run`, 'POST', {});
      notify('Campaign prepared. No ads purchased or external posts sent.');
      openCampaignResult(result);
      await renderCurrentPage(false);
    }
    if (action === 'export') {
      const data = await api('/export');
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = `${state.company.slug}-export-${new Date().toISOString().slice(0, 10)}.json`; anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      notify('Workspace export downloaded. Keep customer data private.');
    }
  } catch (error) { notify(error.message, true); }
  finally {
    element.disabled = false;
    if (!state.switchingWorkspace) document.querySelector('#company-select').disabled = false;
  }
}

function openCampaignResult(result) {
  document.querySelector('#dialog-title').textContent = 'Your campaign is ready to explore.';
  document.querySelector('#dialog-eyebrow').textContent = 'DEMO CAMPAIGN PREPARED';
  const campaign = result.campaign;
  const link = `/site/${encodeURIComponent(state.company.slug)}?campaign=${encodeURIComponent(campaign.sourceCode)}`;
  document.querySelector('#dialog-body').innerHTML = `<div class="campaign-result"><span class="result-mark">${icon('check')}</span><h3>${escapeHtml(campaign.name)}</h3><p>Your content is prepared and your source link is ready. Open the website and submit an enquiry or booking to see the lead arrive with this campaign’s source.</p><div class="result-deliveries">${(result.deliveries || []).map(delivery => `<div><strong>${escapeHtml(channelNames[delivery.channel])}</strong>${badge(delivery.status)}</div>`).join('')}</div><a class="button button-primary full-width" href="${link}" target="_blank" rel="noopener">Try your tracked landing page ${icon('up')}</a><p class="subtle">No external posts, ad purchases, or fabricated performance data.</p></div>`;
  dialog.showModal();
}

document.addEventListener('click', event => { handleAction(event).catch(error => notify(error.message, true)); });
document.addEventListener('change', async event => {
  const { leadStatus, bookingStatus } = event.target.dataset;
  if (!leadStatus && !bookingStatus) return;
  if (state.switchingWorkspace) return;
  const select = event.target;
  select.disabled = true;
  document.querySelector('#company-select').disabled = true;
  try {
    await api(`/${leadStatus ? 'leads' : 'bookings'}/${encodeURIComponent(leadStatus || bookingStatus)}`, 'PATCH', { status: select.value });
    notify(leadStatus ? 'Lead stage updated.' : 'Booking status updated.');
    await renderCurrentPage(false);
  } catch (error) { notify(error.message, true); await renderCurrentPage(false); }
  finally {
    select.disabled = false;
    if (!state.switchingWorkspace) document.querySelector('#company-select').disabled = false;
  }
});

document.querySelector('#close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog && (event.offsetX < 0 || event.offsetY < 0 || event.offsetX > dialog.offsetWidth || event.offsetY > dialog.offsetHeight)) dialog.close(); });
document.querySelector('#new-company-button').addEventListener('click', openCompanyForm);
document.querySelector('#menu-button').addEventListener('click', event => {
  const isOpen = document.querySelector('#sidebar').classList.toggle('mobile-open');
  event.currentTarget.setAttribute('aria-expanded', String(isOpen));
});
document.querySelector('#company-select').addEventListener('change', async event => {
  const selectedCompanyId = event.target.value;
  const sequence = ++state.workspaceSequence;
  // Remove the previous company's controls before loading another workspace.
  // Commit the new company ID only once its settings are available.
  state.switchingWorkspace = true;
  ++state.loadSequence;
  dialog.close();
  event.target.disabled = true;
  document.querySelector('#page-actions').innerHTML = '';
  pageContent.innerHTML = '<div class="loading-card">Opening the selected workspace…</div>';
  try {
    const settings = await request(`/api/companies/${encodeURIComponent(selectedCompanyId)}/settings`);
    if (sequence !== state.workspaceSequence) return;
    state.companyId = selectedCompanyId;
    state.company = settings.company || settings;
    state.data = {};
    state.leadSearch = ''; state.leadStatus = ''; state.bookingStatus = '';
    updateWorkspace();
  } catch (error) {
    if (sequence !== state.workspaceSequence) return;
    event.target.value = state.companyId;
    notify(`Could not switch workspace: ${error.message}`, true);
  } finally {
    if (sequence === state.workspaceSequence) {
      state.switchingWorkspace = false;
      event.target.disabled = false;
      await renderCurrentPage();
    }
  }
});
window.addEventListener('hashchange', () => {
  const view = location.hash.slice(1);
  state.view = views[view] ? view : 'overview';
  document.querySelector('#sidebar').classList.remove('mobile-open');
  document.querySelector('#menu-button').setAttribute('aria-expanded', 'false');
  renderCurrentPage();
});

async function startApplication() {
  try {
    state.session = await request('/api/session');
    state.companyId = state.session.defaultCompanyId || state.session.companies[0].id;
    state.company = await api('/settings');
    state.company = state.company.company || state.company;
    const view = location.hash.slice(1);
    state.view = views[view] ? view : 'overview';
    updateWorkspace();
    await renderCurrentPage();
  } catch (error) {
    pageContent.innerHTML = `<div class="error-card"><h2>Let’s get your workspace running.</h2><p>${escapeHtml(error.message)}</p><p>Start the local server with <code>.\\run.ps1</code>, then reload this page.</p></div>`;
  }
}

startApplication();
