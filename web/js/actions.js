/*
  What a click or a submit does.

  Each handler calls one API method and hands the answer to the store. There
  is no logic here about whether something is allowed -- the server offered
  the action, or it did not appear.
*/

import { api, token } from './api.js';
import { say } from './dom.js';
import {
  S, absorb, again, closeForm, closeMap, go, openForm, openMap, render,
  signOut, toggleCard,
} from './store.js';

const lines = (s) => (s || '').split('\n').map((x) => x.trim()).filter(Boolean);

async function run(work, ok) {
  try {
    const reply = await work();
    /* Every write answers with the whole cell it happened in, which is the
       right subject on a cell page and the wrong one on a page about a single
       task. There, ask for the thing the screen is actually showing. */
    if (S.page === 'task') await again();
    else { absorb(reply); render(); }
    if (ok) say(ok);
  } catch (e) {
    say(e.message, true);
    throw e;
  }
}

export function wireClicks(root) {
  root.addEventListener('click', async (ev) => {
    const el = ev.target.closest('[data-act]');
    if (!el) return;
    const { act, form, cell, id, option, step } = el.dataset;

    switch (act) {
      case 'form': return openForm(form);
      case 'unform': return closeForm(form);
      case 'home': return go(null);
      case 'open': ev.preventDefault(); return go(cell);
      case 'map': return openMap(cell || S.cellId);
      case 'unmap': return closeMap();
      case 'expand': return toggleCard(id);
      case 'signout': return signOut();
      case 'showlog':
        S.log = (await api.history(S.cellId)).events;
        return render();
      case 'hidelog':
        S.log = null;
        return render();
      case 'step':
        return run(() => api.step(id, step, {})).catch(() => {});
      case 'vote':
        return run(() => api.vote(id, option), 'Counted.').catch(() => {});
      case 'take':
        return run(() => api.updateTask(id, { owner_id: S.user.id }), 'Yours.').catch(() => {});
      case 'drop':
        return run(() => api.updateTask(id, { owner_id: null }), 'Handed back.').catch(() => {});
    }
  });
}

export function wireChanges(root) {
  root.addEventListener('change', (ev) => {
    const el = ev.target.closest('[data-act="progress"]');
    if (!el) return;
    run(() => api.updateTask(el.dataset.id, { progress: Number(el.value) })).catch(() => {});
  });
}

export function wireForms(root) {
  root.addEventListener('submit', async (ev) => {
    const f = ev.target.closest('form[data-form]');
    if (!f) return;
    ev.preventDefault();

    const d = Object.fromEntries(new FormData(f).entries());
    const kind = f.dataset.form;
    const id = f.dataset.id;

    try {
      switch (kind) {
        case 'signin': {
          const r = await api.signIn(d.name, d.email);
          token.set(r.token);
          S.user = r.user;
          return go(null);
        }
        case 'cell':
          closeForm('start');
          return go((await api.createCell(d.goal)).cell.id);
        case 'child':
          closeForm('child');
          return go((await api.createCell(d.goal, S.cellId)).cell.id);
        case 'goal':
          closeForm('goal');
          return run(() => api.refineGoal(S.cellId, d.goal), 'Changed.');
        case 'member':
          closeForm('member');
          return run(() => api.admit(S.cellId, {
            name: d.name, email: d.email, role: d.role || 'member',
          }), `${d.name} is in.`);
        case 'decision':
          closeForm('decision');
          return run(() => api.propose(S.cellId, {
            question: d.question,
            detail: d.detail,
            options: lines(d.options),
            work: lines(d.work).length ? { 0: lines(d.work) } : {},
          }), 'Raised.');
        case 'task':
          closeForm('task');
          return run(() => api.addTask(S.cellId, d.title));
        case 'budget':
          closeForm('budget');
          return run(() => api.setCommitments(S.cellId,
            { amount: d.amount, currency: d.currency, due_on: d.due_on }), 'Noted.');
        case 'due':
          closeForm('due:' + id);
          return run(() => api.updateTask(id, { due_on: d.due_on, cost: d.cost }), 'Noted.');
        case 'split':
          closeForm('split:' + id);
          return run(() => api.splitOffTask(id, d.goal), 'It has its own cell now.');
        case 'remark':
          f.reset();
          return run(() => api.remark(id, d.body));
        case 'evidence':
          closeForm('ev:' + id);
          return run(() => api.attachEvidence({
            subject_kind: f.dataset.kind || 'decision', subject_id: id,
            kind: d.kind, label: d.label, ref: d.ref,
          }), 'Attached.');
        case 'step':
          closeForm(`step:${f.dataset.step}:${id}`);
          return run(() => api.step(id, f.dataset.step, d));
      }
    } catch (e) {
      /* run() already said what went wrong; leave the person where they were. */
      render();
    }
  });
}
