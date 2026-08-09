/*
  What the screen is currently showing.

  Everything in here is either something the server sent or something the
  person is in the middle of doing (which card is open, which form is
  showing). No derived business state lives here -- if the interface needs to
  know something, the server said it.
*/

import { api, token } from './api.js';

export const S = {
  user: null,
  page: 'home',       // 'home' | 'cell' | 'map' | 'task'
  routeId: null,      // whatever the hash points at: a cell, or a task
  cellId: null,       // the cell being shown, or the one a task lives in
  taskId: null,
  view: null,
  open: new Set(),    // decision cards expanded
  forms: new Set(),   // inline forms showing
  focus: false,       // a form just opened and should take the cursor
  optionRows: 2,      // how many options the propose form is offering
  keepPlace: true,    // hold the scroll position across a re-render
  log: null,
};

let notify = () => {};

export function onChange(fn) {
  notify = fn;
}

export function render() {
  notify();
}

export function openForm(key) {
  if (key === 'decision' || key.startsWith('ask:')) S.optionRows = 2;
  S.forms.add(key);
  S.focus = true;
  render();
}

export function closeForm(key) {
  S.forms.delete(key);
  render();
}

export const showing = (key) => S.forms.has(key);

export function toggleCard(id) {
  S.open.has(id) ? S.open.delete(id) : S.open.add(id);
  render();
}

/* Every mutation answers with the whole refreshed cell, so the screen never
   has to work out what changed. */
export function absorb(payload) {
  if (payload && payload.cell) {
    S.view = payload;
    S.cellId = payload.cell.id;
    S.log = null;
  }
}

/*
  Where the hash points. The map of a cell is the same cell seen a different
  way, not a different thing, so it is that cell's address with one word in
  front of it.
*/
export function routeOf(hash) {
  const raw = (hash || '').replace(/^#/, '');
  if (raw.startsWith('map/')) {
    const id = raw.slice(4);
    return id ? { page: 'map', cellId: id } : { page: 'home', cellId: null };
  }
  if (raw === 'yours') return { page: 'yours', cellId: null };
  if (raw.startsWith('task/')) {
    const id = raw.slice(5);
    return id ? { page: 'task', cellId: id } : { page: 'home', cellId: null };
  }
  return { page: raw ? 'cell' : 'home', cellId: raw || null };
}

const addressOf = (page, id) =>
  (page === 'yours' ? 'yours'
    : page === 'map' ? `map/${id}`
    : page === 'task' ? `task/${id}` : (id || ''));

export const sameRoute = (a, b) => a.page === b.page && a.cellId === b.cellId;

export async function go(id, page) {
  page = page || (id ? 'cell' : 'home');
  S.open.clear();
  S.forms.clear();
  S.log = null;
  S.keepPlace = false;  // moving between pages is the one time it starts over
  S.page = page;
  S.routeId = id;
  S.taskId = page === 'task' ? id : null;
  S.cellId = page === 'task' ? null : id;
  location.hash = addressOf(page, id);

  if (page === 'yours') {
    S.view = await api.yours();
    return render();
  }
  if (!id) {
    S.page = 'home';
    S.view = await api.home();
    return render();
  }
  try {
    if (page === 'task') {
      S.view = await api.task(id);
      S.cellId = S.view.cell.id;   // so the trail still knows where we are
    } else {
      S.view = await api.cell(id);
    }
  } catch (e) {
    S.page = 'home';
    S.routeId = S.cellId = S.taskId = null;
    location.hash = '';
    S.view = await api.home();
  }
  render();
}

/* Whatever page we are on, load it again -- used after acting on a task, when
   the reply is about the cell but the screen is about the task. */
export const again = () => go(S.routeId, S.page);

/* A person, rather than a place. */
export const openYours = () => go(null, 'yours');

/* The same cell, given the whole page instead of a section of one. */
export const openMap = (cellId) => go(cellId, 'map');
export const closeMap = () => go(S.cellId, 'cell');

export async function boot() {
  if (!token.get()) return render();
  try {
    S.user = (await api.me()).user;
  } catch (e) {
    token.clear();
    return render();
  }
  const at = routeOf(location.hash);
  await go(at.cellId, at.page);
}

export async function signOut() {
  await api.signOut().catch(() => {});
  token.clear();
  S.user = null;
  S.page = 'home';
  S.routeId = S.cellId = S.taskId = null;
  S.view = null;
  location.hash = '';
  render();
}


/* One more thing the cell could choose. Bounded, because a question with nine
   answers is not a question yet. */
export function moreOptions() {
  if (S.optionRows < 6) S.optionRows += 1;
  render();
}
