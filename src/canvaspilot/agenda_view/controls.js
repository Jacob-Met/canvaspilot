(() => {
  'use strict';
  const form = document.getElementById('agenda-filters');
  const course = document.getElementById('course-filter');
  const date = document.getElementById('date-filter');
  const search = document.getElementById('search-filter');
  const entries = [...document.querySelectorAll('.agenda-entry')].map(element => ({
    element,
    text: element.textContent.toLowerCase(),
  }));
  const total = entries.length;
  const groups = ['timed', 'all_day', 'timing_unavailable'];

  function update() {
    const query = search.value.trim().toLowerCase();
    const counts = Object.fromEntries(groups.map(group => [group, 0]));
    for (const { element, text } of entries) {
      const matchesCourse = !course.value || element.dataset.course === course.value;
      const matchesDate = !date.value || element.dataset.group === 'timing_unavailable'
        || element.dataset.date === date.value;
      const matchesText = !query || text.includes(query);
      element.hidden = !(matchesCourse && matchesDate && matchesText);
      if (!element.hidden) counts[element.dataset.group] += 1;
    }
    let visible = 0;
    for (const group of groups) {
      visible += counts[group];
      document.querySelector(`[data-visible-count="${group}"]`).textContent = String(counts[group]);
      document.querySelector(`[data-empty="${group}"]`).hidden = counts[group] !== 0;
    }
    document.getElementById('view-count').textContent = `Showing ${visible} of ${total} saved entries`;
    const courseText = course.value ? `Course ${course.value}` : 'All selected courses';
    const dateText = date.value ? `Source date ${date.value}; unavailable timing retained` : 'All source dates';
    const searchText = search.value.trim() ? `Text: ${search.value.trim()}` : 'No text filter';
    document.getElementById('view-context').textContent = `${courseText} · ${dateText} · ${searchText}`;
  }

  form.addEventListener('input', update);
  form.addEventListener('change', update);
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('reset', () => queueMicrotask(update));
  document.getElementById('view-tools').hidden = false;
  const print = document.getElementById('print-agenda');
  print.hidden = false;
  print.addEventListener('click', () => window.print());

  let disclosureState = null;
  window.addEventListener('beforeprint', () => {
    update();
    disclosureState = [...document.querySelectorAll('.agenda-entry:not([hidden]) .source-details')]
      .map(element => ({ element, open: element.open }));
    for (const { element } of disclosureState) element.open = true;
  });
  window.addEventListener('afterprint', () => {
    for (const { element, open } of disclosureState || []) element.open = open;
    disclosureState = null;
  });
  update();
})();
