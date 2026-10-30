const form = document.querySelector('#report-form');
const message = document.querySelector('#form-message');
const list = document.querySelector('#reports-list');
const filter = document.querySelector('#status-filter');
const categoryFilter = document.querySelector('#category-filter');
const fileInput = document.querySelector('#photo');
const areaBars = document.querySelector('#area-bars');

const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const prettyTime = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return '';
  return new Intl.DateTimeFormat(undefined, {dateStyle:'medium', timeStyle:'short'}).format(date);
};
const statusClass = (status) => status === 'Resolved' ? 'status-resolved' : status === 'In progress' ? 'status-progress' : 'status-submitted';

function renderAreaPulse(reports) {
  const places = new Map();
  for (const report of reports) {
    const label = String(report.location || '').trim();
    const key = label.toLocaleLowerCase();
    if (!key) continue;
    const current = places.get(key) || {label, count: 0};
    current.count += 1;
    places.set(key, current);
  }
  const ranked = [...places.values()].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label)).slice(0, 3);
  if (!ranked.length) {
    areaBars.innerHTML = '<p class="area-empty">Place summary will appear when reports are added.</p>';
    return;
  }
  const highest = ranked[0].count;
  areaBars.innerHTML = ranked.map((place) => `
    <div class="area-row">
      <span class="area-name" title="${esc(place.label)}">${esc(place.label)}</span>
      <span class="area-track"><span class="area-fill" style="width:${Math.max(10, Math.round(place.count / highest * 100))}%"></span></span>
      <span class="area-count">${place.count}</span>
    </div>`).join('');
}

fileInput.addEventListener('change', () => {
  document.querySelector('#photo-label').textContent = fileInput.files[0]?.name || 'Add a photo';
});

async function loadReports() {
  try {
    const response = await fetch('/api/reports');
    if (!response.ok) throw new Error('Could not load reports');
    const data = await response.json();
    const reports = data.reports || [];
    renderAreaPulse(reports);
    document.querySelector('#total-count').textContent = reports.length;
    document.querySelector('#active-count').textContent = data.counts?.['In progress'] || 0;
    document.querySelector('#resolved-count').textContent = data.counts?.Resolved || 0;
    document.querySelector('#feed-count').textContent = reports.length;
    const selectedCategory = categoryFilter.value;
    const categories = [...new Set(reports.map((report) => report.category))].sort((a, b) => a.localeCompare(b));
    categoryFilter.innerHTML = '<option value="all">All categories</option>' + categories.map((category) => `<option value="${esc(category)}">${esc(category)}</option>`).join('');
    if (categories.includes(selectedCategory)) categoryFilter.value = selectedCategory;
    const visible = reports.filter((report) =>
      (filter.value === 'all' || report.status === filter.value) &&
      (categoryFilter.value === 'all' || report.category === categoryFilter.value)
    );
    if (!visible.length) {
      list.innerHTML = `<div class="empty-state"><span class="empty-icon">⌖</span><h3>${reports.length ? 'No reports in this status' : 'It starts with one report'}</h3><p>${reports.length ? 'Choose another status to see more.' : 'Share a local issue and it will appear here for everyone.'}</p></div>`;
      return;
    }
    list.innerHTML = visible.map((report) => `
      <article class="report-card">
        <div class="report-top"><div><h3 class="report-title">${esc(report.title)}</h3><div class="report-meta"><span class="category-tag">${esc(report.category)}</span><span>${esc(prettyTime(report.created_at))}</span></div></div><span class="status-tag ${statusClass(report.status)}">${esc(report.status)}</span></div>
        <p class="report-desc">${esc(report.description)}</p>
        ${report.photo_url ? `<img class="report-photo" src="${esc(report.photo_url)}" alt="Photo attached to ${esc(report.title)}" loading="lazy">` : ''}
        <div class="report-bottom"><span class="report-location">${esc(report.location)}</span><span class="priority ${report.priority === 'High' ? 'high' : ''}">${report.priority === 'High' ? '● HIGH PRIORITY' : 'COMMUNITY REPORT'}</span></div>
        <div class="report-bottom"><span class="report-location">${esc(report.ai_summary)}</span><label><span class="visually-hidden">Update report status</span><select class="status-select" data-report-id="${report.id}" aria-label="Update status for ${esc(report.title)}"><option ${report.status === 'Submitted' ? 'selected' : ''}>Submitted</option><option ${report.status === 'In progress' ? 'selected' : ''}>In progress</option><option ${report.status === 'Resolved' ? 'selected' : ''}>Resolved</option></select></label></div>
      </article>`).join('');
  } catch (error) {
    list.innerHTML = '<div class="empty-state"><h3>Reports could not load</h3><p>Check that the app is running, then refresh.</p></div>';
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  message.textContent = '';
  message.classList.remove('error');
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  button.querySelector('span:first-child').textContent = 'Submitting report…';
  try {
    const response = await fetch('/api/reports', {method:'POST', body:new FormData(form)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Could not submit this report.');
    form.reset();
    document.querySelector('#photo-label').textContent = 'Add a photo';
    message.textContent = 'Your report has been added to the community dashboard.';
    filter.value = 'all';
    categoryFilter.value = 'all';
    await loadReports();
  } catch (error) {
    message.textContent = error.message;
    message.classList.add('error');
  } finally {
    button.disabled = false;
    button.querySelector('span:first-child').textContent = 'Submit community report';
  }
});

list.addEventListener('change', async (event) => {
  const select = event.target.closest('.status-select');
  if (!select) return;
  select.disabled = true;
  try {
    const response = await fetch(`/api/reports/${select.dataset.reportId}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:select.value})});
    if (!response.ok) throw new Error();
    await loadReports();
  } catch {
    message.textContent = 'Status update failed. Please try again.';
    message.classList.add('error');
    await loadReports();
  }
});
filter.addEventListener('change', loadReports);
categoryFilter.addEventListener('change', loadReports);
document.querySelector('#refresh-button').addEventListener('click', loadReports);
loadReports();
setInterval(loadReports, 20000);
