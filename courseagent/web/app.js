/* UW Course Research Agent front-end logic */

const queryInput = document.getElementById('query');
const searchBtn = document.getElementById('search-btn');
const resultsList = document.getElementById('results-list');
const limitationsEl = document.getElementById('limitations');

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value ?? '';
  return div.innerHTML;
}

function renderCitation(citation) {
  const title = citation.source_title || citation.url;
  return `
    <div class="citation">
      <strong>${escapeHtml(citation.claim_field || 'Source')}:</strong>
      ${escapeHtml(citation.evidence_text)}
      <a href="${escapeHtml(citation.url)}" target="_blank" rel="noopener">${escapeHtml(citation.url)}</a>
      ${citation.snapshot_id ? `<span class="freshness">snapshot ${escapeHtml(citation.snapshot_id)}</span>` : ''}
    </div>`;
}

function renderResult(result) {
  const citations = (result.citations || []).map(renderCitation).join('');
  const freshness = result.freshness
    ? `<div class="freshness">Retrieved ${escapeHtml(result.freshness.retrieved_at || 'n/a')} · Snapshot ${escapeHtml(result.freshness.snapshot_id || 'n/a')}</div>`
    : '';
  return `
    <div class="card">
      <h3>${escapeHtml(result.department)} ${escapeHtml(result.course_number)}${result.title ? ' — ' + escapeHtml(result.title) : ''}</h3>
      <div class="meta">${result.credits ? 'Credits: ' + escapeHtml(result.credits) : ''}</div>
      ${result.summary ? `<div class="description">${escapeHtml(result.summary)}</div>` : ''}
      ${freshness}
      ${citations}
    </div>`;
}

function renderLimitations(limitations) {
  if (!limitations || limitations.length === 0) {
    limitationsEl.hidden = true;
    return;
  }
  limitationsEl.hidden = false;
  limitationsEl.innerHTML = `<strong>Limitations:</strong><ul>${limitations.map((l) => `<li>${escapeHtml(l)}</li>`).join('')}</ul>`;
}

async function runSearch() {
  const query = queryInput.value.trim();
  if (!query) return;
  resultsList.innerHTML = '<p>Searching…</p>';
  limitationsEl.hidden = true;
  try {
    const response = await fetch('/course-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await response.json();
    renderLimitations(data.limitations);
    if (!data.results || data.results.length === 0) {
      resultsList.innerHTML = '<p>No matching courses found in approved indexed sources.</p>';
      return;
    }
    resultsList.innerHTML = data.results.map(renderResult).join('');
  } catch (err) {
    resultsList.innerHTML = `<p>Error: ${escapeHtml(String(err))}</p>`;
  }
}

searchBtn.addEventListener('click', runSearch);
queryInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') runSearch();
});
