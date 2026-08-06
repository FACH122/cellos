/*
  One piece of work, with the page to itself.

  A cell page answers "what is going on here". This answers a different
  question -- "what am I supposed to do about this one thing" -- and a row in
  a list is the wrong shape for it. Everything a row had no room for is here:
  why the work exists at all, what has been offered in support of it, who is
  expected to do it and who checks it, and what happens next.

  Nothing here is new information. It is the same task, read closely.
*/

import { esc, meter, plural, when } from '../dom.js';
import { S, showing } from '../store.js';

export function taskPage(v) {
  const t = v.task;
  return [
    head(v, t),
    doing(v, t),
    became(v, t),
    why(v, t),
    who(v, t),
    support(v, t),
  ].filter(Boolean).join('');
}

/* ------------------------------------------------------------------ head */

const STATE_WORD = {
  open: 'nobody has taken this',
  active: 'being done',
  done: 'finished',
  expanded: 'this became a cell',
};

function head(v, t) {
  return `<section class="task-page">
    <div class="row top">
      <h1 class="grow">${esc(t.title)}</h1>
      <button class="quiet faint" data-act="open" data-cell="${v.cell.id}">back to the cell</button>
    </div>
    <div class="pulse">
      <span class="${t.state === 'open' ? 'warn-text' : ''}">${esc(STATE_WORD[t.state] || t.state)}</span>
      ${t.owner_name ? `<span>${esc(t.owner_name)}</span>` : ''}
      <span>${meter(t.progress)} ${t.progress}%</span>
      ${t.due_on ? `<span class="${t.days_left < 0 ? 'warn-text' : 'faint'}">${due(t)}</span>` : ''}
      ${t.cost != null ? `<span class="faint">${esc(String(t.cost))}</span>` : ''}
    </div>
  </section>`;
}

function due(t) {
  if (t.days_left < 0) return `${plural(-t.days_left, 'day')} late`;
  if (t.days_left === 0) return 'due today';
  return `due in ${plural(t.days_left, 'day')}`;
}

/* --------------------------------------------------------------- the work */

/*
  The one section on this page that is a place to act rather than a place to
  read. Everything offered here was offered by the server; nothing below
  works out for itself whether a person is allowed to do it.
*/
function doing(v, t) {
  if (t.state === 'expanded') return '';
  const mine = t.is_yours;
  return `<section><h2>What to do</h2>
    <div class="doing">
      ${t.can_take && !mine
        ? `<p><button class="primary" data-act="take" data-id="${t.id}">
             ${t.owner_id ? 'Take this over' : 'Take this'}</button></p>`
        : ''}
      ${mine
        ? `<p class="sm muted">This is yours.
             <button class="quiet" data-act="drop" data-id="${t.id}">hand it back</button></p>`
        : ''}
      ${t.can_report
        ? `<label class="field"><span>How far along is it?</span>
             <input type="range" min="0" max="100" step="5" value="${t.progress}"
                    data-act="progress" data-id="${t.id}"></label>`
        : ''}
      ${t.can_time
        ? `<p><button class="quiet" data-act="form" data-form="due:${t.id}">
             ${t.due_on || t.cost != null ? 'change the date or cost' : 'add a date or a cost'}
           </button></p>` : ''}
      ${showing('due:' + t.id) ? dueForm(t) : ''}
      ${t.can_expand
        ? `<p class="sm muted">Too big for one person?
             <button class="quiet" data-act="form" data-form="split:${t.id}">make it a cell</button></p>`
        : ''}
      ${showing('split:' + t.id) ? splitForm(t) : ''}
      ${v.you.acts_here
        ? `<p><button class="quiet" data-act="form" data-form="ev:${t.id}">offer evidence</button></p>`
        : ''}
      ${showing('ev:' + t.id) ? evidenceForm(t) : ''}
    </div>
  </section>`;
}

function dueForm(t) {
  return `<form class="panel" data-form="due" data-id="${t.id}">
    <div class="row">
      <label class="field grow"><span>Wanted by</span>
        <input name="due_on" type="date" autofocus value="${esc(t.due_on || '')}"></label>
      <label class="field grow"><span>What it cost</span>
        <input name="cost" inputmode="decimal" value="${t.cost == null ? '' : t.cost}"
               placeholder="leave empty for none"></label>
    </div>
    <div class="actions"><button class="primary" type="submit">Save</button>
      <button type="button" class="quiet" data-act="unform" data-form="due:${t.id}">cancel</button>
    </div></form>`;
}

function splitForm(t) {
  return `<form class="panel" data-form="split" data-id="${t.id}">
    <label class="field"><span>What would that group's goal be?</span>
      <input name="goal" required autofocus value="${esc(t.title)}"></label>
    <p class="xs faint">This work is not replaced or copied. It becomes that cell's
      mission, and its progress becomes that cell's progress.</p>
    <div class="actions"><button class="primary" type="submit">Make it a cell</button>
      <button type="button" class="quiet" data-act="unform" data-form="split:${t.id}">cancel</button>
    </div></form>`;
}

function evidenceForm(t) {
  return `<form class="panel" data-form="evidence" data-kind="task" data-id="${t.id}">
    <div class="row">
      <label class="field" style="width:8rem"><span>Kind</span>
        <select name="kind"><option value="link">link</option>
          <option value="note">note</option><option value="file">file</option></select></label>
      <label class="field grow"><span>What is it</span>
        <input name="label" required autofocus></label>
    </div>
    <label class="field"><span>Where (optional)</span><input name="ref"></label>
    <div class="actions"><button class="primary" type="submit">Attach</button>
      <button type="button" class="quiet" data-act="unform" data-form="ev:${t.id}">cancel</button>
    </div></form>`;
}

/* ------------------------------------------------------ what it grew into */

function became(v, t) {
  if (!v.became) return '';
  return `<section><h2>It became a cell</h2>
    <div class="child" data-act="open" data-cell="${v.became.id}">
      <span class="goal"><span class="glyph cell" aria-hidden="true">◎</span>${esc(v.became.goal)}</span>
      <span class="xs faint">${plural(v.became.people, 'person', 'people')}</span>
      ${meter(t.progress)}
      <span class="xs faint" style="width:2.5rem;text-align:right">${t.progress}%</span>
    </div>
    <p class="xs faint">This work did not stop existing. It is that cell's mission,
      and the figure above is that cell's progress.</p>
  </section>`;
}

/* ----------------------------------------------------------------- origin */

function why(v, t) {
  if (!v.because) return '';
  return `<section class="aside"><h2>Why this exists</h2>
    <p class="sm">Nobody typed this in. It appeared when the cell settled
      <button class="quiet" data-act="open" data-cell="${v.because.cell_id}">“${
        esc(v.because.question)}”</button></p>
  </section>`;
}

/* --------------------------------------------------------- responsibility */

const ROLE_WORD = {
  responsible: 'doing it',
  verifier: 'checks it',
  leader: 'answers for it',
  participant: 'took part',
};

function who(v, t) {
  const roles = t.responsibility && t.responsibility.roles;
  if (!roles) return '';
  const lines = Object.keys(ROLE_WORD)
    .filter((r) => (roles[r] || []).length)
    .map((r) => `<div class="row sm">
      <span class="who-role faint">${esc(ROLE_WORD[r])}</span>
      <span>${roles[r].map((p) => esc(p.name)).join(', ')}</span>
    </div>`);
  if (!lines.length) return '';
  return `<section class="aside"><h2>Who is expected to do what</h2>
    <div class="stack">${lines.join('')}</div>
    <p class="xs faint">Derived, not assigned — read off who holds the work,
      who leads here, and who leads the cell above.</p>
  </section>`;
}

/* --------------------------------------------------------------- evidence */

function support(v, t) {
  if (!v.evidence.length) return '';
  return `<section class="aside"><h2>Offered in support</h2>
    <div class="evidence stack">${v.evidence.map((e) => `<div class="row sm">
      <span class="kind">${esc(e.kind)}</span>
      ${e.ref ? `<a href="${esc(e.ref)}" target="_blank" rel="noopener">${esc(e.label)}</a>`
              : `<span>${esc(e.label)}</span>`}
      <span class="xs faint">${esc(e.added_by_name || '')} · ${esc(when(e.added_at))}</span>
    </div>`).join('')}</div>
  </section>`;
}
