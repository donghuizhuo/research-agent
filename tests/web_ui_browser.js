await page.open('__APP_URL__');
async function check(name, fn) {
  if (!await page.eval(fn)) throw new Error(`FAIL: ${name} ${JSON.stringify(await page.eval(() => ({body:document.body.innerText,query:document.querySelector('#query-input').value})))}`);
  console.log(`PASS: ${name}`);
}
async function query(value, department = '') {
  await page.eval(`() => {const q=document.querySelector('#query-input');q.value=${JSON.stringify(value)};document.querySelector('#department-filter').value=${JSON.stringify(department)};}`);
  await page.click('.primary-button');
  await page.wait(700);
}
await check('detail initially hidden', () => document.querySelector('.detail-panel').hidden);
const screenshotQuery = 'show me information about the cse 143';
await query(screenshotQuery);
await check('screenshot query returns only CSE 143 and opens cited detail', () =>
  document.querySelector('#result-count').textContent === '1 result' &&
  document.querySelector('#answer-type').textContent === 'Direct match' &&
  document.querySelectorAll('.result-card').length === 1 &&
  document.querySelector('.result-card').innerText.includes('CSE 143') &&
  document.querySelector('#detail-heading').textContent === 'CSE 143' &&
  !document.querySelector('.detail-panel').hidden &&
  document.querySelector('#course-sources a')?.href.startsWith('https://www.washington.edu/'));
await query('');
await check('empty input guidance', () => document.querySelector('#status-region').innerText.includes('Enter a course'));
// Delay the real API, rather than replacing its success response.
await page.eval(() => {
  window.originalFetch = window.fetch;
  window.requests = [];
  window.fetch = async (url, options) => {
    window.requests.push({url, body: options?.body});
    if (url === '/course-search') await new Promise(resolve => setTimeout(resolve, 400));
    return window.originalFetch(url, options);
  };
  document.querySelector('#query-input').value = 'CSE-142';
});
await page.click('.primary-button');
await check('loading visible and submit disabled', () => !document.querySelector('#loading-state').hidden && document.querySelector('.primary-button').disabled);
await page.wait(1100);
await check('exact real detail auto-opens, absent fields honest', () =>
  !document.querySelector('.detail-panel').hidden && document.querySelector('#detail-heading').textContent === 'CSE 142' &&
  document.querySelector('#detail-body').innerText.includes('Unavailable from indexed sources') &&
  document.querySelector('#course-sources').querySelector('a')?.href.startsWith('https://www.washington.edu/'));
await check('detail endpoint invoked', () => window.requests.some(request => request.url.startsWith('/courses/CSE-142?workflow_id=')));
await page.click('[data-evidence="description"]');
await check('source evidence reachable from field', () => document.activeElement.id === 'sources-heading');
await page.eval(() => {window.fetch=window.originalFetch;});
await query('intro programming courses');
await check('natural language real results and reset detail', () => document.querySelectorAll('.result-card').length === 3 && document.querySelector('.detail-panel').hidden);
await page.click('.result-card[data-result="1"]');
await page.wait(400);
await check('selected result detail loads', () => !document.querySelector('.detail-panel').hidden && document.querySelector('.result-card[aria-current="true"]'));
await query('', 'INFO');
await check('department browsing', () => document.querySelectorAll('.result-card').length === 1 && document.querySelector('.result-card').innerText.includes('INFO 201'));
await query('CSE 999');
await check('empty results clear stale cards', () => document.querySelector('#result-count').textContent === '0 results' && !document.querySelector('#empty-state').hidden && document.querySelectorAll('.result-card').length === 0);
await page.eval(() => {
 const q=document.querySelector('#query-input');q.value='CSE14';q.focus();q.dispatchEvent(new Event('input',{bubbles:true}));
});
await page.wait(900);
await check('real API-backed prefix suggestions', () => !document.querySelector('#typeahead-list').hidden && document.querySelector('.typeahead-option').innerText.includes('CSE 142'));
await page.press('ArrowDown');
await check('keyboard focuses suggestion', () => document.activeElement.classList.contains('typeahead-option'));
await page.press('Enter');
await page.wait(900);
await check('keyboard suggestion auto-opens exact detail', () => document.querySelector('#detail-heading').textContent === 'CSE 142' && !document.querySelector('.detail-panel').hidden);
await page.eval(() => {document.querySelector('#query-input').value='CSE 143';document.querySelector('#query-input').focus();});
await page.press('Enter');await page.wait(900);
await check('Enter submits and preserves workflow', () => document.querySelector('#detail-heading').textContent === 'CSE 143');
await query(screenshotQuery);
await check('screenshot query in reused workflow stays exact', () =>
  document.querySelector('#result-count').textContent === '1 result' &&
  document.querySelector('#detail-heading').textContent === 'CSE 143' &&
  !document.querySelector('.detail-panel').hidden);
// HTTP errors must not be mistaken for successful empty results.
await page.eval(() => {window.fetch=async()=>new Response('{}',{status:500});});
await query('programming');
await check('HTTP search error and loading recovery', () => document.querySelector('#answer-type').textContent === 'Search failed' && !document.querySelector('.primary-button').disabled && document.querySelector('#loading-state').hidden);
await page.eval(() => {window.fetch=async()=>{throw new TypeError('Failed to fetch');};});
await query('programming');
await check('network search error', () => document.querySelector('#status-region').innerText.includes('could not search'));
await page.eval(() => {window.fetch=window.originalFetch;});
await query('programming');
await page.eval(() => {window.fetch=async(url, options)=>url.startsWith('/courses/')?new Response('{}',{status:404}):window.originalFetch(url,options);});
await page.click('.result-card');await page.wait(300);
await check('detail error supports retry', () => document.querySelector('#detail-body').innerText.includes('Select the course again to retry'));
await page.eval(() => {window.fetch=window.originalFetch;});
await page.click('.result-card');await page.wait(300);
await check('detail retry succeeds', () => document.querySelector('#detail-body').innerText.includes('Credits'));
// A late detail response must not repopulate detail after a new search.
await page.eval(() => {
 window.fetch=async(url,options)=>{
  const response=await window.originalFetch(url,options);
  if(url.startsWith('/courses/')) await new Promise(resolve=>setTimeout(resolve,700));
  return response;
 };
});
await page.click('.result-card');
await query('CSE 999');await page.wait(500);
await check('late detail response ignored', () => document.querySelector('.detail-panel').hidden && document.querySelector('#result-count').textContent === '0 results');
await page.eval(() => {window.fetch=window.originalFetch;});
console.log('WEB_UI_PASS');
