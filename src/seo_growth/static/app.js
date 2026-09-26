const statusGrid = document.querySelector('#status-grid');
const onboarding = document.querySelector('#onboarding');
const opportunitiesElement = document.querySelector('#opportunities');
const changesElement = document.querySelector('#changes');
const toast = document.querySelector('#toast');

const escapeHtml = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

const request = async (url, options = {}) => {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || 'The request failed');
  return body;
};

const showToast = (message) => {
  toast.textContent = message;
  toast.classList.remove('hidden');
  window.setTimeout(() => toast.classList.add('hidden'), 4500);
};

const statusCard = (label, ready, readyText = 'Connected') => `
  <div class="card status-card">
    <div class="status-label">${label}</div>
    <div class="status-value ${ready ? 'ready' : 'pending'}">${ready ? readyText : 'Setup needed'}</div>
  </div>`;

const loadStatus = async () => {
  const status = await request('/api/status');
  statusGrid.innerHTML = [
    statusCard('Website files', status.site_directory_ready, 'Found'),
    statusCard('Visitor counts', status.google_analytics_ready),
    statusCard('Google searches', status.search_console_ready),
    statusCard('AI suggestions', status.openai_ready),
  ].join('');
  onboarding.classList.toggle('hidden', status.search_console_ready);
};

const loadOpportunities = async () => {
  const opportunities = await request('/api/opportunities');
  if (!opportunities.length) {
    opportunitiesElement.innerHTML = '<div class="card empty">No search data yet. Load sample data or connect Google.</div>';
    return;
  }
  opportunitiesElement.innerHTML = opportunities.map((item, index) => `
    <article class="card opportunity">
      <div>
        <h3>${escapeHtml(item.query)}</h3>
        <p>${escapeHtml(item.reason)}</p>
        <div class="metrics">
          <span class="score">Score ${item.score}</span>
          <span>${item.impressions} displays</span>
          <span>${item.clicks} visits</span>
          <span>Position ${item.position.toFixed(1)}</span>
          <span>${escapeHtml(item.page)}</span>
        </div>
      </div>
      <button class="secondary" data-draft="${index}">Draft improvement</button>
    </article>`).join('');
};

const loadChanges = async () => {
  const changes = await request('/api/changes');
  if (!changes.length) {
    changesElement.innerHTML = '<div class="card empty">No changes have been drafted.</div>';
    return;
  }
  changesElement.innerHTML = changes.map((item) => `
    <article class="card change">
      <div>
        <h3><span class="pill">${escapeHtml(item.status)}</span>${escapeHtml(item.page)} · ${escapeHtml(item.field)}</h3>
        <p>${escapeHtml(item.new_value)}</p>
      </div>
      ${item.status === 'proposed' ? `<button class="primary" data-apply="${item.id}">Apply edit</button>` : ''}
    </article>`).join('');
};

const withBusyButton = async (button, action) => {
  const label = button.textContent;
  button.disabled = true;
  button.textContent = 'Working…';
  try { await action(); } catch (error) { showToast(error.message); }
  finally { button.disabled = false; button.textContent = label; }
};

document.querySelector('#demo-button').addEventListener('click', (event) => withBusyButton(event.currentTarget, async () => {
  await request('/api/import/demo', { method: 'POST' });
  await loadOpportunities();
  showToast('Sample data loaded. These numbers are demonstrations, not real visitors.');
}));

document.querySelector('#sync-button').addEventListener('click', (event) => withBusyButton(event.currentTarget, async () => {
  const result = await request('/api/sync/google', { method: 'POST' });
  await loadOpportunities();
  showToast(`Imported ${result.search_metrics} Google search rows.`);
}));

opportunitiesElement.addEventListener('click', (event) => {
  const button = event.target.closest('[data-draft]');
  if (!button) return;
  withBusyButton(button, async () => {
    await request(`/api/opportunities/${button.dataset.draft}/draft`, { method: 'POST' });
    await loadChanges();
    showToast('Two SEO edits were drafted.');
  });
});

changesElement.addEventListener('click', (event) => {
  const button = event.target.closest('[data-apply]');
  if (!button) return;
  withBusyButton(button, async () => {
    await request(`/api/changes/${button.dataset.apply}/apply`, { method: 'POST' });
    await loadChanges();
    showToast('Website file updated. Review its Git diff before publishing.');
  });
});

Promise.all([loadStatus(), loadOpportunities(), loadChanges()]).catch((error) => showToast(error.message));
