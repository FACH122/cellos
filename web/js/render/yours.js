/*
  One person, across everything they can see.

  This used to be a section on a cell page, which meant "what is on me" got
  asked once per cell and answered half at a time -- the other half was in a
  cell you had to remember to go and look at. A person does not have a
  separate self per cell.

  What has happened lately is derived the same way everything else is: a query
  over the log for things other people did to things that are yours. There is
  no notification table, no unread flag and nothing to mark as read, so it
  cannot fall out of step with what actually happened, and there is no badge
  with a number on it -- a count of unread items measures the software, not
  the work.
*/

import { CELL_MARK, TASK_MARK, esc, meter, plural, when } from '../dom.js';
import { S } from '../store.js';

export function yoursPage(v) {
  const c = v.carried;
  if (!c) {
    return `<section style="margin-top:var(--s7)"><h1>Yours</h1>
      <p class="muted">You are not in any cell yet.</p></section>`;
  }
  return [
    head(v, c),
    onYou(v, c),
    holding(v, c),
    waitingFor(v, c),
    unclaimed(v, c),
    lately(v),
    leading(v, c),
  ].filter(Boolean).join('');
}

const goalOf = (v, cellId) => v.cells[cellId] || 'somewhere';

function head(v, c) {
  const n = c.yours.length;
  return `<section>
    <h1>${esc(S.user.name)}</h1>
    <div class="pulse">
      <span>${n ? `${plural(n, 'thing')} in your hands` : 'nothing in your hands'}</span>
      ${n ? `<span>${meter(c.progress.percent)} ${c.progress.percent}%</span>` : ''}
      <span class="faint">across ${plural(Object.keys(v.cells).length, 'cell')}</span>
    </div>
  </section>`;
}

/* ------------------------------------------------------- waiting on you */

/*
  The only part of this page that is a demand rather than a report: nobody
  else can move until this person does something.
*/
function onYou(v, c) {
  const w = c.waiting_on_you;
  const items = [
    ...w.votes.map((d) => askRow(v, d, 'your vote')),
    ...w.decisions.map((d) => askRow(v, d, 'only you can settle this')),
    ...w.not_started.map((t) => taskLine(v, t, 'you hold this and have not started')),
  ];
  if (!items.length) return '';
  return `<section><h2>Waiting on you</h2>${items.join('')}</section>`;
}

function askRow(v, d, why) {
  return `<div class="carried waiting">
    <button class="quiet" data-act="open" data-cell="${d.cell_id}">“${esc(d.question)}”</button>
    <span class="xs faint">${esc(why)} · ${esc(goalOf(v, d.cell_id))}</span>
  </div>`;
}

/* ------------------------------------------------------------ your work */

function holding(v, c) {
  if (!c.yours.length) return '';
  return `<section><h2>In your hands</h2>
    ${c.yours.map((t) => taskLine(v, t)).join('')}
  </section>`;
}

function taskLine(v, t, note) {
  return `<div class="task">
    <a class="title" href="#task/${t.id}" target="_blank" rel="noopener"
       >${TASK_MARK}${esc(t.title)}</a>
    <span class="xs faint nowrap">${esc(note || goalOf(v, t.cell_id))}</span>
    ${meter(t.progress)}
    <span class="pct">${t.progress}%</span>
  </div>`;
}

/* ------------------------------------------------------- waiting on others */

function waitingFor(v, c) {
  const b = c.you_are_waiting_on;
  const items = [
    ...b.work.map((t) => `<div class="task">
      <a class="title" href="#task/${t.id}" target="_blank" rel="noopener"
         >${TASK_MARK}${esc(t.title)}</a>
      <span class="owner">${esc(t.owner_name || 'somebody')}</span>
      ${meter(t.progress)}<span class="pct">${t.progress}%</span>
    </div>`),
    ...b.questions.map((d) => askRow(v, d, 'you have voted; it is not settled')),
  ];
  if (!items.length) return '';
  return `<section class="aside"><h2>You are waiting on</h2>${items.join('')}</section>`;
}

/* ----------------------------------------------------------- nobody's yet */

function unclaimed(v, c) {
  if (!c.blocked.length) return '';
  return `<section class="aside"><h2>Nobody has taken</h2>
    ${c.blocked.map((t) => taskLine(v, t)).join('')}
    <p class="xs faint">Work with no owner is the commonest reason a cell stops.</p>
  </section>`;
}

/* --------------------------------------------------------------- the news */

function lately(v) {
  if (!v.lately.length) return '';
  /*
    One line of plain sentence, and the where-and-when underneath it in the
    quiet size. Pinning a time to the left and a cell to the right reads fine
    on a wide screen and shreds the sentence on a narrow one.
  */
  return `<section><h2>What has happened</h2>
    <div class="lately">${v.lately.map((n) => `<div class="note">
      <span class="sm">${esc(n.who)} — ${n.subject
        ? (String(n.subject_id).startsWith('task_')
            ? `<a href="#task/${n.subject_id}" target="_blank" rel="noopener">${esc(n.subject)}</a>`
            : `<button class="quiet" data-act="open" data-cell="${n.cell_id}">${esc(n.subject)}</button>`)
        : 'something'} ${esc(n.said)}</span>
      <span class="xs faint">${esc(when(n.at))} · ${esc(n.cell_goal)}</span>
    </div>`).join('')}</div>
  </section>`;
}

/* ------------------------------------------------------------ what you lead */

function leading(v, c) {
  if (!c.cells_led.length) return '';
  return `<section class="aside"><h2>You lead</h2>
    ${c.cells_led.map((cell) => `<div class="child" data-act="open" data-cell="${cell.id}">
      <span class="goal">${CELL_MARK}${esc(cell.goal)}</span>
      <span class="xs faint">${plural(cell.people, 'person', 'people')}</span>
      ${meter(cell.percent)}
      <span class="xs faint" style="width:2.5rem;text-align:right">${cell.percent}%</span>
    </div>`).join('')}
  </section>`;
}
