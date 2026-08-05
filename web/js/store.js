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
  page: 'home',       // 'home' | 'cell' | 'map'
  cellId: null,
  view: null,
  open: new Set(),    // decision cards expanded
  forms: new Set(),   // inline forms showing
  focus: false,       // a form just opened and should take the cursor
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
  return { page: raw ? 'cell' : 'home', cellId: raw || null };
}

const addressOf = (page, cellId) =>
  (page === 'map' ? `map/${cellId}` : (cellId || ''));

export const sameRoute = (a, b) => a.page === b.page && a.cellId === b.cellId;

export async function go(cellId, page) {
  page = page || (cellId ? 'cell' : 'home');
  S.open.clear();
  S.forms.clear();
  S.log = null;
  S.keepPlace = false;  // moving between cells is the one time the page starts over
  S.page = page;
  S.cellId = cellId;
  location.hash = addressOf(page, cellId);

  if (!cellId) {
    S.page = 'home';
    S.view = await api.home();
    return render();
  }
  try {
    S.view = await api.cell(cellId);
  } catch (e) {
    S.page = 'home';
    S.cellId = null;
    location.hash = '';
    S.view = await api.home();
  }
  render();
}

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
  S.cellId = null;
  S.view = null;
  location.hash = '';
  render();
}
