/* Wiring. The only file that touches the page's top-level elements. */

import { wireChanges, wireClicks, wireForms } from './actions.js';
import { esc } from './dom.js';
import { S, boot, go, onChange, routeOf, sameRoute, signOut } from './store.js';
import { cellPage } from './render/cell.js';
import { crumbs, entry, homePage, mapPage } from './render/shell.js';
import { taskPage } from './render/task.js';
import { yoursPage } from './render/yours.js';
import { mountMap, whenOpened } from './render/structure.js';
import { apply as applyTheme, cycle as cycleTheme, describe, label } from './theme.js';

const app = document.getElementById('app');
const bar = document.getElementById('bar');

function render() {
  if (!S.user) {
    bar.hidden = true;
    app.innerHTML = entry();
    focusFirst();
    return;
  }

  bar.hidden = false;
  document.getElementById('who').innerHTML =
    `<button data-act="yours" class="quiet${S.page === 'yours' ? ' here' : ''}">${
      esc(S.user.name)}</button>`
    + `<button data-act="theme" class="quiet" title="${esc(describe())}">${esc(label())}</button>`
    + '<button data-act="signout" class="quiet">sign out</button>';
  document.getElementById('path').innerHTML = crumbs();

  /* The whole page is rebuilt on every action. Holding the scroll position is
     what makes that feel like the page changed rather than reloaded. */
  const y = window.scrollY;
  document.body.dataset.page = S.page;
  app.innerHTML = S.page === 'map' ? mapPage(S.view)
    : S.page === 'yours' ? yoursPage(S.view)
    : S.page === 'task' ? taskPage(S.view)
    : S.cellId ? cellPage(S.view) : homePage(S.view);
  if (S.keepPlace !== false) window.scrollTo(0, y);
  S.keepPlace = true;

  /* `autofocus` does nothing on markup inserted after parse, and focusing on
     every render would yank the cursor out of whatever someone is typing. So
     a form focuses itself exactly once, when it opens. */
  if (S.focus) {
    S.focus = false;
    focusFirst('form ');
  }

  /* The map is the one part of the page that is not rebuilt from a string:
     it keeps its own element so expansion state and positions survive, and
     so it has something to animate. */
  if (S.view && S.view.structure) {
    mountMap(app.querySelector('[data-map]'), S.view.structure);
  }
}

whenOpened((cellId) => go(cellId));

function focusFirst(scope = '') {
  const first = app.querySelector(scope + '[autofocus]');
  if (first) first.focus();
}

onChange(render);
wireClicks(app);
wireChanges(app);
wireForms(app);

bar.addEventListener('click', (ev) => {
  const el = ev.target.closest('[data-act]');
  if (!el) return;
  if (el.dataset.act === 'theme') {
    cycleTheme();
    return render();
  }
  if (el.dataset.act === 'yours') go(null, 'yours');
  if (el.dataset.act === 'home') go(null);
  if (el.dataset.act === 'open') go(el.dataset.cell);
  if (el.dataset.act === 'signout') signOut();
});

window.addEventListener('hashchange', () => {
  const want = routeOf(location.hash);
  if (!sameRoute(want, { page: S.page, cellId: S.routeId })) go(want.cellId, want.page);
});

/* The map on its own page is sized to the window, so it is re-sized with it. */
let resizing = null;
window.addEventListener('resize', () => {
  if (S.page !== 'map') return;
  clearTimeout(resizing);
  resizing = setTimeout(render, 120);
});

applyTheme();
boot();
