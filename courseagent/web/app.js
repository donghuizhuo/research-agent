/* Search and detail use the existing API; suggestions are bounded search results. */
(() => {
  const $ = (id) => document.getElementById(id);
  const ui = {
    form: $('search-form'), query: $('query-input'), department: $('department-filter'),
    suggestions: $('typeahead-list'), status: $('status-region'), loading: $('loading-state'),
    limitations: $('limitations'), results: $('results-list'), empty: $('empty-state'),
    count: $('result-count'), answer: $('answer-type'), grid: $('runtime-grid'),
    detail: document.querySelector('.detail-panel'), detailHeading: $('detail-heading'),
    detailBody: $('detail-body'), submit: document.querySelector('[type="submit"]'),
  };
  let workflowId = null;
  let searchGeneration = 0;
  let detailGeneration = 0;
  let suggestionGeneration = 0;
  let suggestionTimer;
  let searchController;
  let detailController;
  let suggestionController;
  let currentResults = [];
  let suggestedCourses = [];

  function escapeHtml(value) {
    const node = document.createElement('span');
    node.textContent = value ?? '';
    return node.innerHTML;
  }

  function sourceUrl(value) {
    try {
      const url = new URL(value);
      return ['https:', 'http:'].includes(url.protocol) ? url.href : null;
    } catch { return null; }
  }

  async function request(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  }

  function searchRequest(query, signal, session = null) {
    return request('/course-search', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, signal,
      body: JSON.stringify({ query, ...(session ? { workflow_id: session } : {}) }),
    });
  }

  function status(message, kind = 'success') {
    ui.status.innerHTML = message ? `<div class="status-message ${kind}">${escapeHtml(message)}</div>` : '';
  }

  function showLimitations(items) {
    ui.limitations.hidden = !items.length;
    ui.limitations.innerHTML = items.length
      ? `<strong>Search notes</strong><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : '';
  }

  function hideSuggestions() {
    clearTimeout(suggestionTimer);
    suggestionController?.abort();
    suggestionGeneration++;
    ui.suggestions.hidden = true;
    ui.suggestions.innerHTML = '';
    suggestedCourses = [];
    ui.query.setAttribute('aria-expanded', 'false');
  }

  function scheduleSuggestions() {
    hideSuggestions();
    const value = ui.query.value.trim();
    if (value.length < 2) return;
    const generation = suggestionGeneration;
    const department = ui.department.value;
    suggestionTimer = setTimeout(async () => {
      suggestionController = new AbortController();
      // An incomplete course code cannot use exact lookup. Browse the API's
      // department results and match the prefix locally; this is not exhaustive.
      const prefix = value.match(/^(CSE|INFO)(?:\s|-)*(\d{0,3})$/i);
      const query = prefix ? (prefix[2].length === 3 ? `${prefix[1]} ${prefix[2]}` : prefix[1]) : value;
      try {
        const data = await searchRequest(query, suggestionController.signal);
        if (generation !== suggestionGeneration) return;
        const term = prefix ? `${prefix[1]} ${prefix[2]}`.trim().toLowerCase() : value.toLowerCase();
        suggestedCourses = (data.results || []).filter((course) =>
          (!department || course.department === department) &&
          (!prefix || `${course.department} ${course.course_number}`.toLowerCase().startsWith(term))
        ).slice(0, 5);
        if (!suggestedCourses.length) return;
        ui.suggestions.innerHTML = suggestedCourses.map((course, index) => `
          <button class="typeahead-option" type="button" data-suggestion="${index}">
            <strong>${escapeHtml(label(course))}</strong>
            <span>${escapeHtml(course.credits ?? 'Credits unavailable')}${course.credits != null ? ' credits' : ''}</span>
          </button>`).join('');
        ui.suggestions.hidden = false;
        ui.query.setAttribute('aria-expanded', 'true');
      } catch (error) {
        // Suggestions are optional. Explicit Search still reports service errors.
        if (error.name !== 'AbortError' && generation === suggestionGeneration) hideSuggestions();
      }
    }, 300);
  }

  function label(course) {
    return `${course.department} ${course.course_number}${course.title ? ` — ${course.title}` : ''}`;
  }

  function freshness(course) {
    const values = course.freshness || {};
    const citations = course.citations || [];
    // Only use timestamps actually returned by the service.
    const retrieved = values.retrieved_at || citations.find((item) => item.retrieved_at)?.retrieved_at;
    const snapshot = values.snapshot_id || citations.find((item) => item.snapshot_id)?.snapshot_id;
    return `<span class="freshness-row"><span>Retrieved: ${escapeHtml(retrieved || 'Unavailable')}</span><span>Snapshot: ${escapeHtml(snapshot || 'Unavailable')}</span></span>`;
  }

  function resetDetail() {
    detailGeneration++;
    detailController?.abort();
    ui.detail.hidden = true;
    ui.detailBody.innerHTML = '';
    ui.grid.classList.remove('detail-open');
  }

  function renderResults(data, department) {
    currentResults = (data.results || []).filter((course) => !department || course.department === department);
    const notes = [...(data.limitations || [])];
    if (department) notes.push(`Showing ${department} courses from the returned matches. Department browsing returns up to 25 courses.`);
    for (const conflict of data.conflicts || []) notes.push(conflict.message || `Conflicting information for ${conflict.course_id}: ${conflict.field}.`);
    showLimitations(notes);
    ui.answer.textContent = ({direct_answer: 'Direct match', ranked_courses: 'Ranked matches', clarification_needed: 'Please clarify', no_results: 'No results'})[data.answer_type] || 'Search complete';
    ui.count.textContent = `${currentResults.length} ${currentResults.length === 1 ? 'result' : 'results'}`;
    ui.empty.hidden = Boolean(currentResults.length);
    if (!currentResults.length) {
      ui.empty.innerHTML = `<h3>${data.answer_type === 'clarification_needed' ? 'Tell us more about the course you want' : 'No matching courses'}</h3><p>Try a course code, another topic, or a different department.</p>`;
      ui.results.innerHTML = '';
      status('No courses to display. Check the search notes and try another search.', 'warning');
      return;
    }
    ui.results.innerHTML = currentResults.map((course, index) => `
      <div role="listitem"><button class="result-card" type="button" data-result="${index}" aria-current="false">
        <span class="result-card__inner"><span class="result-card__top"><span><span class="rank-badge">#${index + 1}</span><strong>${escapeHtml(label(course))}</strong></span></span>
        <span class="result-card__facts"><span class="fact-chip">${escapeHtml(course.credits ?? 'Credits unavailable')}${course.credits != null ? ' credits' : ''}</span><span class="fact-chip citation-count">${(course.citations || []).length} sources</span></span>
        <span class="result-summary">${escapeHtml(course.summary || 'Description unavailable from indexed sources')}</span>${freshness(course)}</span>
      </button></div>`).join('');
    status(`Showing ${currentResults.length} ${currentResults.length === 1 ? 'course' : 'courses'}. Select a course for details.`);
  }

  async function runSearch(event) {
    event?.preventDefault();
    hideSuggestions();
    const department = ui.department.value;
    // The API requires a nonempty query; a bare department is supported.
    const input = ui.query.value.trim();
    const code = input.match(/^(CSE|INFO)[\s-]*(\d{3})$/i);
    const query = code ? `${code[1].toUpperCase()} ${code[2]}` : input || department;
    if (!query) {
      status('Enter a course code, topic, or question, or choose a department.', 'error');
      ui.query.focus();
      return;
    }
    const generation = ++searchGeneration;
    searchController?.abort();
    searchController = new AbortController();
    resetDetail();
    ui.results.innerHTML = '';
    ui.empty.hidden = true;
    ui.loading.hidden = false;
    ui.submit.disabled = true;
    ui.form.setAttribute('aria-busy', 'true');
    ui.count.textContent = 'Searching';
    ui.answer.textContent = 'Searching';
    status('');
    showLimitations([]);
    try {
      const data = await searchRequest(query, searchController.signal, workflowId);
      if (generation !== searchGeneration) return;
      workflowId = data.workflow_id;
      $('workflow-id').textContent = 'active';
      $('state-ref').textContent = 'Catalog search';
      if (new URLSearchParams(location.search).has('debug')) {
        $('debug-session').hidden = false;
        $('debug-workflow').textContent = workflowId;
      }
      renderResults(data, department);
      $('results-heading').focus({preventScroll: true});
      if (data.answer_type === 'direct_answer' && currentResults.length === 1) selectCourse(currentResults[0]);
    } catch (error) {
      if (generation !== searchGeneration || error.name === 'AbortError') return;
      ui.answer.textContent = 'Search failed';
      ui.count.textContent = '0 results';
      ui.empty.hidden = false;
      ui.empty.innerHTML = '<h3>Search could not be completed</h3><p>Try again in a moment.</p>';
      status('We could not search courses. Please try again.', 'error');
    } finally {
      if (generation === searchGeneration) {
        ui.loading.hidden = true;
        ui.submit.disabled = false;
        ui.form.setAttribute('aria-busy', 'false');
      }
    }
  }

  function renderCitation(item) {
    const url = sourceUrl(item.url);
    return `<details class="citation-detail"><summary>${escapeHtml(item.claim_field || 'Course source')} · ${escapeHtml(item.source_title || 'Source')}</summary>
      <div class="citation-detail__body"><blockquote>${escapeHtml(item.evidence_text)}</blockquote>
      ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.source_title || url)}</a>` : '<p>Source link unavailable</p>'}
      <div class="meta-grid"><div><span>Snapshot</span>${escapeHtml(item.snapshot_id || 'Unavailable')}</div><div><span>Retrieved</span>${escapeHtml(item.retrieved_at || 'Unavailable')}</div><div><span>Indexed</span>${escapeHtml(item.indexed_at || 'Unavailable')}</div></div></div></details>`;
  }

  function renderDetail(course) {
    const citations = course.citations || [];
    const fields = [['Title', 'title'], ['Credits', 'credits'], ['Description', 'description'], ['Prerequisites', 'prerequisites'], ['Corequisites', 'corequisites']];
    ui.detailBody.innerHTML = `<div class="course-title-block"><h3>${escapeHtml(label(course))}</h3></div>
      ${(course.limitations || []).length ? `<div class="status-message warning"><ul>${course.limitations.map((note) => `<li>${escapeHtml(note)}</li>`).join('')}</ul></div>` : ''}
      <dl class="fact-list">${fields.map(([name, field]) => {
        const evidence = course.field_provenance?.[field] || citations.filter((item) => item.claim_field === field);
        return `<div class="fact-row"><div class="fact-row__header"><dt>${name}</dt><button type="button" class="link-button" data-evidence="${field}">${evidence.length ? `View ${evidence.length} source${evidence.length === 1 ? '' : 's'}` : 'View course sources'}</button></div><dd>${course[field] != null && course[field] !== '' ? escapeHtml(course[field]) : '<span class="unavailable">Unavailable from indexed sources</span>'}</dd></div>`;
      }).join('')}</dl>
      <section class="citation-panel" aria-labelledby="sources-heading"><h4 id="sources-heading" tabindex="-1">Sources and catalog dates</h4>${freshness(course)}
      ${!Object.keys(course.field_provenance || {}).length && !citations.some((item) => item.claim_field) ? '<p>Sources are provided for this course; individual field attribution is unavailable.</p>' : ''}
      <div id="course-sources">${citations.length ? citations.map(renderCitation).join('') : '<p>Source evidence unavailable from indexed sources.</p>'}</div></section>`;
    ui.detailBody.querySelectorAll('[data-evidence]').forEach((button) => {
      button.addEventListener('click', () => {
        const field = button.dataset.evidence;
        const grouped = course.field_provenance?.[field] || citations.filter((item) => item.claim_field === field);
        $('course-sources').innerHTML = (grouped.length ? grouped : citations).map(renderCitation).join('') || '<p>Source evidence unavailable from indexed sources.</p>';
        $('sources-heading').focus();
      });
    });
  }

  async function selectCourse(course) {
    const generation = ++detailGeneration;
    detailController?.abort();
    detailController = new AbortController();
    ui.detail.hidden = false;
    ui.grid.classList.add('detail-open');
    ui.detailHeading.textContent = `${course.department} ${course.course_number}`;
    $('detail-route').textContent = 'Course details';
    ui.detailBody.innerHTML = '<p role="status">Loading course details…</p>';
    ui.detail.setAttribute('aria-busy', 'true');
    for (const card of ui.results.querySelectorAll('[data-result]')) {
      card.setAttribute('aria-current', String(currentResults[Number(card.dataset.result)]?.course_id === course.course_id));
    }
    try {
      const query = workflowId ? `?workflow_id=${encodeURIComponent(workflowId)}` : '';
      const data = await request(`/courses/${encodeURIComponent(course.course_id)}${query}`, {signal: detailController.signal});
      if (generation !== detailGeneration) return;
      renderDetail(data);
      ui.detailHeading.focus();
    } catch (error) {
      if (generation !== detailGeneration || error.name === 'AbortError') return;
      ui.detailBody.innerHTML = '<p role="alert">Course details could not be loaded. Select the course again to retry.</p>';
    } finally {
      if (generation === detailGeneration) ui.detail.setAttribute('aria-busy', 'false');
    }
  }

  ui.form.addEventListener('submit', runSearch);
  ui.query.addEventListener('input', scheduleSuggestions);
  ui.department.addEventListener('change', scheduleSuggestions);
  ui.query.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') hideSuggestions();
    if (event.key === 'ArrowDown' && !ui.suggestions.hidden) {
      event.preventDefault();
      ui.suggestions.querySelector('button')?.focus();
    }
  });
  ui.suggestions.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { hideSuggestions(); ui.query.focus(); }
    if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      const buttons = [...ui.suggestions.querySelectorAll('button')];
      const step = event.key === 'ArrowDown' ? 1 : -1;
      buttons[(buttons.indexOf(document.activeElement) + step + buttons.length) % buttons.length]?.focus();
    }
  });
  ui.suggestions.addEventListener('click', (event) => {
    const button = event.target.closest('[data-suggestion]');
    const course = button && suggestedCourses[Number(button.dataset.suggestion)];
    if (!course) return;
    ui.query.value = `${course.department} ${course.course_number}`;
    ui.department.value = course.department;
    ui.form.requestSubmit();
  });
  document.addEventListener('click', (event) => { if (!event.target.closest('.field--query')) hideSuggestions(); });
  ui.results.addEventListener('click', (event) => {
    const button = event.target.closest('[data-result]');
    if (button) selectCourse(currentResults[Number(button.dataset.result)]);
  });
  document.querySelectorAll('[data-query]').forEach((button) => button.addEventListener('click', () => {
    ui.query.value = button.dataset.query;
    ui.department.value = '';
    ui.form.requestSubmit();
  }));
})();
