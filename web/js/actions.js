/*
  What a click or a submit does.

  Each handler calls one API method and hands the answer to the store. There
  is no logic here about whether something is allowed -- the server offered
  the action, or it did not appear.
*/

import { api, token } from './api.js';
import { say } from './dom.js';
import {
  S, absorb, again, closeForm, closeMap, go, moreOptions, openForm, openMap, render,
  signOut, toggleCard,
} from './store.js';

const lines = (s) => (s || '').split('\n').map((x) => x.trim()).filter(Boolean);

/*
  The option rows, read back.

  Empty rows are dropped, and the work is keyed by the position an option ends
  up in rather than the row it was typed in -- the server enumerates the
  options it is given, so leaving row two blank and filling row three would
  otherwise attach the wrong consequences to the wrong answer.
*/
function chosen(d) {
  const options = [];
  const work = {};
  for (let i = 0; i < 6; i += 1) {
    const text = (d['option' + i] || '').trim();
    if (!text) continue;
    work[String(options.length)] = lines(d['work' + i]);
    options.push(text);
  }
  return { options, work };
}

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
      /* Open the cell with that question already unfolded, rather than
         landing on a page where it is one collapsed card among several. */
      case 'openq': S.open.add(id); return go(cell);
      case 'moreoption': return moreOptions();
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

/*
  Type a name, get an address.

  The email is the identity here -- it is what decides who you are -- but on a
  local system nobody wants to invent one every time they sign in as somebody
  else. So the name fills it in, and stops the moment you type in the field
  yourself, because a guess should never overwrite an answer.
*/
const addressFor = (name) => {
  const slug = (name || '').trim().toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')   // "Bergström" -> "bergstrom"
    .replace(/[^a-z0-9]+/g, '.')
    .replace(/^\.+|\.+$/g, '');
  return slug ? `${slug}@gmail.com` : '';
};

export function wireTyping(root) {
  root.addEventListener('input', (ev) => {
    const f = ev.target.closest('form[data-form="signin"]');
    if (!f) return;
    if (ev.target.name === 'email') { ev.target.dataset.own = '1'; return; }
    if (ev.target.name !== 'name' || f.email.dataset.own) return;
    f.email.value = addressFor(ev.target.value);
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
        case 'decision': {
          closeForm('decision');
          const { options, work } = chosen(d);
          return run(() => api.propose(S.cellId, {
            question: d.question, detail: d.detail, options, work,
          }), 'Raised.');
        }
        case 'task':
          closeForm('task');
          return run(() => api.addTask(S.cellId, d.title));
        case 'budget': {
          closeForm('budget');
          /* One form, two facts. The goal is only rewritten if somebody
             actually changed it, so opening the panel to set a date does not
             put a GoalRefined event in the permanent record. */
          const goal = (d.goal || '').trim();
          const moved = goal && goal !== S.view.cell.goal;
          return run(async () => {
            if (moved) await api.refineGoal(S.cellId, goal);
            return api.setCommitments(S.cellId,
              { amount: d.amount, currency: d.currency, due_on: d.due_on });
          }, moved ? 'Saved.' : 'Noted.');
        }
        case 'due':
          closeForm('due:' + id);
          return run(() => api.updateTask(id, { due_on: d.due_on, cost: d.cost }), 'Noted.');
        case 'note':
          closeForm('note:' + id);
          return run(() => api.noteOnTask(id, d.body), 'Posted.');
        case 'ask':
          closeForm('ask:' + id);
          return run(() => api.propose(S.cellId, {
            question: d.question, detail: d.detail,
            options: lines(d.options), work: {}, about: id,
          }), 'Asked.');
        case 'split':
          closeForm('split:' + id);
          return run(() => api.splitOffTask(id, d.goal), 'It has its own cell now.');
        case 'remark':
          f.reset();
          return run(() => api.remark(id, d.body, f.dataset.option));
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
