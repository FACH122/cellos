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

export async function go(cellId) {
  S.open.clear();
  S.forms.clear();
  S.log = null;
  S.keepPlace = false;  // moving between cells is the one time the page starts over
  S.cellId = cellId;
  location.hash = cellId || '';

  if (!cellId) {
    S.view = await api.home();
    return render();
  }
  try {
    S.view = await api.cell(cellId);
  } catch (e) {
    S.cellId = null;
    location.hash = '';
    S.view = await api.home();
  }
  render();
}

export async function boot() {
  if (!token.get()) return render();
  try {
    S.user = (await api.me()).user;
  } catch (e) {
    token.clear();
    return render();
  }
  await go(location.hash.slice(1) || null);
}

export async function signOut() {
  await api.signOut().catch(() => {});
  token.clear();
  S.user = null;
  S.cellId = null;
  S.view = null;
  location.hash = '';
  render();
}
