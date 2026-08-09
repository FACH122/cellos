/*
  One piece of work, with the page to itself.

  A cell page answers "what is going on here". This answers a different
  question -- "what am I supposed to do about this one thing" -- and it is
  the only page in CellOS where somebody is meant to sit for a while rather
  than glance and move on.

  So it is laid out as a desk rather than a record:

    the head      what this is and where it stands, in one line
    the bar       every action, together, once -- not scattered down the page
    the work      what has actually happened to it, and what people said
                  while doing it; this is the middle of the page because it
                  is the middle of the job
    the margin    why it exists, who answers for it, what backs it up

  Nothing in the record is stored. Every line of it was already an event; the
  only place you could see them before was the whole cell's log, mixed in with
  everything else that happened that week.
*/

import { TASK_MARK, esc, meter, plural, when } from '../dom.js';
import { happened } from '../labels.js';
import { S, showing } from '../store.js';

export function taskPage(v) {
  const t = v.task;
  return [
    head(v, t),
    bar(v, t),
    panels(v, t),
    work(v, t),
    became(v, t),
    margin(v, t),
  ].filter(Boolean).join('');
}

/* ------------------------------------------------------------------ head */

const STANDS = {
  open: ['nobody has taken this', 'warn-text'],
  active: ['being done', ''],
  done: ['finished', 'good-text'],
  expanded: ['this became a cell', ''],
};

function head(v, t) {
  const [word, tone] = STANDS[t.state] || [t.state, ''];
  return `<section class="task-page">
    <nav class="row xs faint" aria-label="where this sits">
      <button class="quiet" data-act="open" data-cell="${v.cell.id}"
        >← ${esc(v.cell.goal)}</button>
    </nav>
    <h1>${TASK_MARK}${esc(t.title)}</h1>
    <div class="standing">
      <span class="${tone}">${esc(word)}</span>
      ${t.owner_name
        ? `<span>${t.is_yours ? 'yours' : esc(t.owner_name)}</span>`
        : ''}
      <span class="grow-bar">${meter(t.progress)} <b>${t.progress}%</b></span>
      ${t.due_on ? `<span class="${t.days_left < 0 ? 'warn-text' : 'faint'}">
        <time datetime="${esc(t.due_on)}">${due(t)}</time></span>` : ''}
      ${t.cost != null ? `<span class="faint">cost ${esc(String(t.cost))}</span>` : ''}
    </div>
  </section>`;
}

function due(t) {
  if (t.days_left < 0) return `${plural(-t.days_left, 'day')} late`;
  if (t.days_left === 0) return 'due today';
  return `due in ${plural(t.days_left, 'day')}`;
}

/* ------------------------------------------------------------------- bar */

/*
  Everything a person can do here, on one line, in the order they would want
  it: take it, move it, say something, add a date, hand it to a group. It was
  a column of five paragraphs, each with one small button in it, which read
  as a list of features rather than a set of tools.
*/
function bar(v, t) {
  if (t.state === 'expanded') return '';
  const acts = [];

  if (t.can_take && !t.is_yours) {
    acts.push(`<button class="primary" data-act="take" data-id="${t.id}">${
      t.owner_id ? 'Take this over' : 'Take this'}</button>`);
  }
  if (t.is_yours) {
    acts.push(`<button data-act="drop" data-id="${t.id}">Hand it back</button>`);
  }
  if (v.you.acts_here) {
    acts.push(`<button data-act="form" data-form="note:${t.id}">Add a note</button>`);
    acts.push(`<button data-act="form" data-form="ev:${t.id}">Attach evidence</button>`);
  }
  if (t.can_time) {
    acts.push(`<button data-act="form" data-form="due:${t.id}">${
      t.due_on || t.cost != null ? 'Date or cost' : 'Add a date or cost'}</button>`);
  }
  if (t.can_expand) {
    acts.push(`<button data-act="form" data-form="split:${t.id}">Make it a cell</button>`);
  }
  if (!acts.length) return '';

  return `<section class="bar-section">
    ${t.can_report ? `<label class="slider">
      <span class="xs faint">How far along</span>
      <input type="range" min="0" max="100" step="5" value="${t.progress}"
             aria-label="How far along is this work"
             data-act="progress" data-id="${t.id}">
    </label>` : ''}
    <div class="toolbar" role="group" aria-label="what you can do">${acts.join('')}</div>
  </section>`;
}

/* Panels open under the bar, not wherever their button used to be. */
function panels(v, t) {
  return [
    showing('note:' + t.id) ? noteForm(t) : '',
    showing('due:' + t.id) ? dueForm(t) : '',
    showing('ev:' + t.id) ? evidenceForm(t) : '',
    showing('split:' + t.id) ? splitForm(t) : '',
  ].filter(Boolean).join('');
}

function noteForm(t) {
  return `<form class="panel" data-form="note" data-id="${t.id}">
    <label class="field"><span>What is happening with this?</span>
      <textarea name="body" required autofocus rows="3"
        placeholder="What you found, what is in the way, what you tried."></textarea></label>
    <div class="actions"><button class="primary" type="submit">Post</button>
      <button type="button" class="quiet" data-act="unform" data-form="note:${t.id}">cancel</button>
    </div></form>`;
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
          <option value="note">note</option><option value="document">document</option>
          <option value="measurement">measurement</option></select></label>
      <label class="field grow"><span>What is it</span>
        <input name="label" required autofocus></label>
    </div>
    <label class="field"><span>Where (optional)</span>
      <input name="ref" placeholder="https://…"></label>
    <div class="actions"><button class="primary" type="submit">Attach</button>
      <button type="button" class="quiet" data-act="unform" data-form="ev:${t.id}">cancel</button>
    </div></form>`;
}

/* ------------------------------------------------------------- the record */

/*
  Notes and events in one column, oldest first, because that is the order the
  work happened in and reading it top to bottom is reading the story.

  A note says something a person chose to say. An event is something the
  system observed. Both belong here and they are drawn differently: the note
  has a voice, the event is a line of small grey text.
*/
function work(v, t) {
  const lines = [
    ...v.notes.map((n) => ({
      at: n.said_at,
      html: `<article class="note-said">
        <header class="xs faint"><b>${esc(n.author_name || 'someone')}</b>
          · <time datetime="${esc(n.said_at)}">${esc(when(n.said_at))}</time></header>
        <p>${esc(n.body)}</p>
      </article>`,
    })),
    ...v.record.map((e) => ({
      at: e.at,
      html: `<div class="did xs">
        <time datetime="${esc(e.at)}" class="faint">${esc(when(e.at))}</time>
        <span>${esc(said(e))}</span>
      </div>`,
    })),
  ].sort((a, b) => (a.at < b.at ? -1 : a.at > b.at ? 1 : 0));

  return `<section><h2>The work</h2>
    ${lines.length
      ? `<div class="log-of-work">${lines.map((l) => l.html).join('')}</div>`
      : '<p class="empty">Nothing has happened to this yet.</p>'}
    ${v.you.acts_here && !showing('note:' + t.id)
      ? `<p><button class="quiet" data-act="form" data-form="note:${t.id}"
           >Say what is happening</button></p>` : ''}
  </section>`;
}

/* The log already has words for these; this page only adds a subject. */
function said(e) {
  const who = e.who;
  switch (e.type) {
    case 'TaskCreated': return `${who} added this`;
    case 'TaskGenerated': return 'this appeared when a decision was settled';
    case 'TaskAssigned': return e.payload.owner_id
      ? `${who} took it on` : `${who} handed it back`;
    case 'ProgressUpdated': return `${who} moved it to ${e.payload.progress}%`;
    case 'TaskCompleted': return `${who} finished it`;
    case 'TaskReopened': return `${who} reopened it`;
    case 'TaskExpanded': return `${who} made it a cell`;
    case 'DeadlineSet': return e.payload.due_on
      ? `${who} wanted it by ${e.payload.due_on}` : `${who} cleared the date`;
    case 'CostRecorded': return `${who} recorded a cost of ${e.payload.cost}`;
    case 'EvidenceAttached': return `${who} attached evidence`;
    default: return happened({ type: e.type, actor_name: who }) || `${who} did something`;
  }
}

/* ------------------------------------------------------ what it grew into */

function became(v, t) {
  if (!v.became) return '';
  return `<section><h2>It became a cell</h2>
    <div class="child" data-act="open" data-cell="${v.became.id}">
      <span class="goal"><span class="glyph cell" aria-hidden="true">◎</span>${
        esc(v.became.goal)}</span>
      <span class="xs faint">${plural(v.became.people, 'person', 'people')}</span>
      ${meter(t.progress)}
      <span class="xs faint" style="width:2.5rem;text-align:right">${t.progress}%</span>
    </div>
    <p class="xs faint">This work did not stop existing. It is that cell's mission,
      and the figure above is that cell's progress.</p>
  </section>`;
}

/* ---------------------------------------------------------------- margin */

const ROLE_WORD = {
  responsible: 'doing it',
  verifier: 'checks it',
  leader: 'answers for it',
  participant: 'took part',
};

function margin(v, t) {
  const roles = (t.responsibility && t.responsibility.roles) || {};
  const who = Object.keys(ROLE_WORD)
    .filter((r) => (roles[r] || []).length)
    .map((r) => `<div class="who-row">
      <span class="who-role faint">${esc(ROLE_WORD[r])}</span>
      <span>${roles[r].map((p) => esc(p.name)).join(', ')}</span>
    </div>`).join('');

  const parts = [];
  if (v.because) {
    parts.push(`<div class="margin-block">
      <h3>Why this exists</h3>
      <p class="sm">Nobody typed this in. It appeared when the cell settled
        <button class="quiet" data-act="open" data-cell="${v.because.cell_id}"
          >“${esc(v.because.question)}”</button></p>
    </div>`);
  }
  if (who) {
    parts.push(`<div class="margin-block">
      <h3>Who is expected to do what</h3>
      ${who}
      <p class="xs faint">Derived, not assigned — read off who holds the work,
        who leads here, and who leads the cell above.</p>
    </div>`);
  }
  if (v.evidence.length) {
    parts.push(`<div class="margin-block">
      <h3>Offered in support</h3>
      <div class="evidence stack">${v.evidence.map((e) => `<div class="row sm">
        <span class="kind">${esc(e.kind)}</span>
        ${e.ref ? `<a href="${esc(e.ref)}" target="_blank" rel="noopener">${esc(e.label)}</a>`
                : `<span>${esc(e.label)}</span>`}
      </div>`).join('')}</div>
    </div>`);
  }
  if (!parts.length) return '';
  return `<section class="aside margin"><h2>About this work</h2>${parts.join('')}</section>`;
}
