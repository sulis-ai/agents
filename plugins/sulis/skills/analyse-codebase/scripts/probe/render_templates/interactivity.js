// /sulis:analyse-codebase CODE_INTELLIGENCE.html interactivity (vanilla JS, no deps).
// ~150 lines. Inlined into the HTML at render time.

(function () {
  'use strict';

  // ─── Collapsible cards ───────────────────────────────────────────────
  function initCollapse() {
    document.querySelectorAll('section.card h2').forEach(function (h) {
      h.addEventListener('click', function () {
        h.parentElement.classList.toggle('collapsed');
      });
    });
  }

  // ─── Sortable tables ─────────────────────────────────────────────────
  function initSortableTables() {
    document.querySelectorAll('table.sortable').forEach(function (table) {
      var headers = table.querySelectorAll('th');
      headers.forEach(function (th, idx) {
        th.addEventListener('click', function () {
          // Clear sort indicators on siblings
          headers.forEach(function (other) {
            if (other !== th) other.classList.remove('sort-asc', 'sort-desc');
          });

          var asc = !th.classList.contains('sort-asc');
          th.classList.toggle('sort-asc', asc);
          th.classList.toggle('sort-desc', !asc);

          var tbody = table.querySelector('tbody');
          if (!tbody) return;
          var rows = Array.from(tbody.rows);
          var numeric = th.dataset.type === 'number';

          rows.sort(function (a, b) {
            var av = (a.cells[idx] || {}).innerText || '';
            var bv = (b.cells[idx] || {}).innerText || '';
            if (numeric) {
              var an = parseFloat(av.replace(/[^\d.-]/g, '')) || 0;
              var bn = parseFloat(bv.replace(/[^\d.-]/g, '')) || 0;
              return asc ? an - bn : bn - an;
            }
            return asc ? av.localeCompare(bv) : bv.localeCompare(av);
          });

          rows.forEach(function (row) { tbody.appendChild(row); });
        });
      });
    });
  }

  // ─── Filter inputs ───────────────────────────────────────────────────
  function initFilterInputs() {
    document.querySelectorAll('.filter-input').forEach(function (input) {
      var targetSel = input.dataset.target;
      if (!targetSel) return;
      input.addEventListener('input', function () {
        var q = input.value.toLowerCase().trim();
        var rows = document.querySelectorAll(targetSel + ' tbody tr');
        rows.forEach(function (row) {
          row.style.display = (!q || row.innerText.toLowerCase().indexOf(q) >= 0)
            ? '' : 'none';
        });
        // Same for recommendation cards
        var cards = document.querySelectorAll(targetSel + ' .recommendation');
        cards.forEach(function (card) {
          card.style.display = (!q || card.innerText.toLowerCase().indexOf(q) >= 0)
            ? '' : 'none';
        });
      });
    });
  }

  // ─── Scroll-spy sidebar navigation ───────────────────────────────────
  function initScrollSpy() {
    var navLinks = document.querySelectorAll('nav.sidebar a[href^="#"]');
    if (!navLinks.length) return;

    var sections = Array.from(navLinks).map(function (link) {
      var id = link.getAttribute('href').slice(1);
      return { link: link, el: document.getElementById(id) };
    }).filter(function (s) { return s.el; });

    function update() {
      var scrollPos = window.scrollY + 120;
      var current = sections[0];
      for (var i = 0; i < sections.length; i++) {
        if (sections[i].el.offsetTop <= scrollPos) current = sections[i];
      }
      sections.forEach(function (s) {
        s.link.classList.toggle('active', s === current);
      });
    }

    window.addEventListener('scroll', update, { passive: true });
    update();
  }

  // ─── Init on load ─────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    initCollapse();
    initSortableTables();
    initFilterInputs();
    initScrollSpy();
  }
})();
