/*
  One cell.

  Every section below is drawn only if the server sent the key it needs. A
  two-person cell is not sent a dashboard, so there is no branch here that
  hides one -- there is simply nothing to draw.
*/

import { esc, meter, plural, when } from '../dom.js';
import { happened } from '../labels.js';
import { S, showing } from '../store.js';

import { card } from './decision.js';
import { mapMount, mapCaption } from './structure.js';
import { health } from './health.js';

/*
  How many names to show before the list stops being a list.

  Below COMFORTABLE, a cell is a group whose members you know, and the names
  are worth reading -- so all of them appear and there is nothing to expand.
  Above it, "who are these people" stops being a question anybody asks; the
  ones that matter are whoever leads, and the rest is a number. The server
  already sorts leaders first, so showing the front of the list shows them.
*/
const COMFORTABLE = 8;
const AT_A_GLANCE = 5;

export function cellPage(v) {
  return [
    goal(v),
    health(v),
    mission(v),
    people(v),
    questions(v),
    work(v),
    yours(v),
    inside(v),
    analytics(v),
    settled(v),
    knowledge(v),
    record(v),
  ].filter(Boolean).join('');
}

/* ------------------------------------------------------------------ goal */

function goal(v) {
  const p = v.progress;
  return `<section>
    ${showing('goal')
      ? `<form class="panel" data-form="goal">
           <label class="field"><span>The goal</span>
             <input name="goal" required autofocus value="${esc(v.cell.goal)}"></label>
           <div class="actions"><button class="primary" type="submit">Save</button>
             <button type="button" class="quiet" data-act="unform" data-form="goal">cancel</button>
           </div></form>`
      : `<div class="row top"><h1 class="grow">${esc(v.cell.goal)}</h1>
           ${v.you.is_leader
             ? '<button class="quiet faint" data-act="form" data-form="goal">edit</button>' : ''}
         </div>`}
    <div class="pulse">
      <span>${v.scale === 1 ? 'just you' : plural(v.scale, 'person', 'people')}</span>
      ${p.task_count
        ? `<span>${meter(p.percent)} ${p.percent}%</span>
           <span class="faint">${p.remaining
             ? plural(p.remaining, 'thing') + ' left' : 'everything done'}</span>`
        : '<span class="faint">nothing being done yet</span>'}
      ${v.constraints && v.constraints.budget
        ? `<span class="${v.constraints.budget.over ? 'over' : 'faint'}">${
            esc(v.constraints.budget.reads)}</span>` : ''}
      ${v.constraints && v.constraints.due
        ? dueMarker(v.constraints.due.due_on, v.constraints.due.days_left) : ''}
      ${v.you.is_leader
        ? `<button class="quiet faint" data-act="form" data-form="budget">${
            committed(v) ? 'change' : 'add a budget or a date'}</button>`
        : ''}
    </div>
    ${showing('budget') ? commitmentForm(v) : ''}
  </section>`;
}

const committed = (v) => !!(v.constraints && (v.constraints.budget || v.constraints.due));

/*
  Both commitments in one form, because they are one thought: what this cell
  has said it will hold itself to. Neither is required, and emptying a field
  drops that commitment -- which is a different thing from committing to zero,
  or from having missed a date.
*/
function commitmentForm(v) {
  const b = (v.constraints && v.constraints.budget) || {};
  const d = (v.constraints && v.constraints.due) || {};
  return `<form class="panel" data-form="budget">
    <div class="row">
      <label class="field grow"><span>What is this cell willing to spend?</span>
        <input name="amount" inputmode="decimal" autofocus
               value="${b.amount === undefined ? '' : b.amount}"
               placeholder="leave empty for no budget"></label>
      <label class="field" style="width:6rem"><span>Currency</span>
        <input name="currency" value="${esc(b.currency || 'EUR')}"></label>
      <label class="field grow"><span>Wanted by</span>
        <input name="due_on" type="date" value="${esc(d.due_on || '')}"></label>
    </div>
    <p class="xs faint">Both optional. Spending is the sum of what the work cost,
      rolled up from the cells inside. Nothing is enforced — CellOS will say when
      the money is close or the date has passed, and leave the rest to you.</p>
    <div class="actions"><button class="primary" type="submit">Save</button>
      <button type="button" class="quiet" data-act="unform" data-form="budget">cancel</button>
    </div></form>`;
}

/* ---------------------------------------------------------------- people */

function people(v) {
  const small = v.members.length <= COMFORTABLE;
  const all = small || showing('people');
  const shown = all ? v.members : v.members.slice(0, AT_A_GLANCE);
  const hidden = v.members.length - shown.length;

  return `<section><h2>People</h2>
    <div class="people">
      ${shown.map((m) => `<span class="chip${m.id === S.user.id ? ' you' : ''}">${esc(m.name)}${
        m.role === 'leader' ? '<span class="tag">leads</span>' : ''}</span>`).join('')}
      ${hidden
        ? `<button class="quiet faint" data-act="form" data-form="people">and ${hidden} more</button>`
        : ''}
      ${!small && showing('people')
        ? '<button class="quiet faint" data-act="unform" data-form="people">show fewer</button>' : ''}
    </div>
    ${showing('member')
      ? `<form class="panel" data-form="member">
           <label class="field"><span>Name</span><input name="name" required autofocus></label>
           <label class="field"><span>Email</span><input name="email" type="email" required></label>
           ${v.you.is_leader ? `<label class="field"><span>Role</span>
             <select name="role"><option value="member">member</option>
             <option value="leader">leader</option></select></label>` : ''}
           <div class="actions"><button class="primary" type="submit">Add</button>
             <button type="button" class="quiet" data-act="unform" data-form="member">cancel</button>
           </div></form>`
      : (v.you.can_admit
          ? '<p><button data-act="form" data-form="member">Bring someone in</button></p>' : '')}
  </section>`;
}

/* ------------------------------------------------------------- decisions */

function questions(v) {
  return `<section><h2>Open questions</h2>
    ${v.open_decisions.length
      ? v.open_decisions.map((d) => card(v, d)).join('')
      : '<p class="empty">Nothing waiting on anyone.</p>'}
    ${showing('decision')
      ? proposeForm()
      : (v.you.acts_here
          ? '<p><button data-act="form" data-form="decision">Ask the cell something</button></p>' : '')}
  </section>`;
}

function proposeForm() {
  return `<form class="panel" data-form="decision">
    <label class="field"><span>What has to be decided together?</span>
      <input name="question" required autofocus placeholder="Where do we hold it?"></label>
    <label class="field"><span>Anything worth knowing first (optional)</span>
      <textarea name="detail"></textarea></label>
    <label class="field"><span>The options, one per line (optional)</span>
      <textarea name="options" placeholder="The garden&#10;The hall"></textarea></label>
    <label class="field"><span>If the first option wins, what has to happen? One per line (optional)</span>
      <textarea name="work" placeholder="Put down the deposit&#10;Confirm the date"></textarea></label>
    <div class="actions"><button class="primary" type="submit">Ask it</button>
      <button type="button" class="quiet" data-act="unform" data-form="decision">cancel</button>
    </div></form>`;
}

/* ------------------------------------------------------------------ work */

function taskRow(v, t) {
  /* Work that became a cell is no longer work here. It reads as what it is:
     a group with a goal, one click away. */
  if (t.state === 'expanded') {
    return `<div class="task expanded" data-act="open" data-cell="${t.expanded_into}">
      <span class="title">${esc(t.title)}
        <div class="from">now the mission of a cell${
          t.expanded_people ? ' of ' + plural(t.expanded_people, 'person', 'people') : ''
        }</div></span>
      <span class="owner">open it →</span>
      ${meter(t.progress)}
      <span class="pct">${t.progress}%</span>
    </div>`;
  }

  const canMove = v.you.acts_here && (t.owner_id === S.user.id || !t.owner_id || v.you.is_leader);
  const key = 'split:' + t.id;
  return `<div class="task${t.state === 'done' ? ' done' : ''}">
    <span class="title">${esc(t.title)}</span>
    ${t.can_expand && !showing(key)
      ? `<button class="quiet faint" data-act="form" data-form="${key}">too large</button>` : ''}
    ${t.owner_id
      ? `<span class="owner">${esc(t.owner_name)}</span>`
      : (v.you.acts_here
          ? `<button class="quiet" data-act="take" data-id="${t.id}">take this</button>`
          : '<span class="owner faint">nobody yet</span>')}
    ${canMove
      ? `<input type="range" min="0" max="100" step="5" value="${t.progress}"
           data-act="progress" data-id="${t.id}">`
      : meter(t.progress)}
    <span class="pct">${t.progress}%</span>
    ${marks(t)}
  </div>${showing(key) ? splitForm(t, key) : ''}${
    showing('due:' + t.id) ? dueForm(t) : ''}`;
}

/*
  A due date sits with the progress bar rather than beside it: how far along
  and how long left are one thought. It only raises its voice when the date
  starts to matter — a quiet date, then a warm one, then a loud one.
*/
const CALENDAR = `<svg class="cal" viewBox="0 0 12 12" aria-hidden="true">
  <rect x="1" y="2.5" width="10" height="8" rx="1.5" fill="none"
        stroke="currentColor" stroke-width="1"/>
  <path d="M1 5h10M4 1.5v2M8 1.5v2" stroke="currentColor" stroke-width="1"/></svg>`;

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

/*
  What a task has committed to, and the way in to changing it -- all on the
  row itself. A date and a cost each take the space they need and no more,
  and when there are neither, the whole affordance is one faint character at
  the end of the line rather than a line of its own.
*/
function marks(t) {
  if (t.state === 'expanded') return '';
  const key = 'due:' + t.id;
  const bits = [];
  if (t.due_on && t.state !== 'done') bits.push(dueMarker(t.due_on, t.days_left));
  if (t.cost) bits.push(`<span class="due calm">${esc(String(t.cost))}</span>`);
  if (!t.can_time) return bits.join('');

  return `<button class="marks" data-act="form" data-form="${key}"
    title="${bits.length ? 'Change the date or cost' : 'Add a date or a cost'}"
    >${bits.length ? bits.join('') : '<span class="ellipsis">···</span>'}</button>`;
}

/* The same quiet marker wherever a date appears: on a task, or on the cell. */
function dueMarker(iso, daysLeft) {
  const [tone, said] = dueWords(daysLeft, iso);
  return `<span class="due ${tone}">${tone === 'calm' ? CALENDAR : '<i></i>'}${esc(said)}</span>`;
}

function dueWords(left, iso) {
  if (left === undefined || left === null) return ['calm', shortDate(iso)];
  if (left < 0) return ['late', `${plural(-left, 'day')} overdue`];
  if (left === 0) return ['near', 'Due today'];
  if (left === 1) return ['near', 'Due tomorrow'];
  if (left <= 3) return ['near', `${left} days left`];
  return ['calm', shortDate(iso)];
}

function shortDate(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return `${MONTHS[m - 1]} ${d}`;
}

/* Opened from the row's own control, and closed again the moment it is saved. */
function dueForm(t) {
  return `<form class="panel" data-form="due" data-id="${t.id}">
    <div class="row">
      <label class="field grow"><span>Wanted by</span>
        <input name="due_on" type="date" value="${esc(t.due_on || '')}" autofocus></label>
      <label class="field grow"><span>What it cost</span>
        <input name="cost" inputmode="decimal"
               value="${t.cost === null || t.cost === undefined ? '' : t.cost}"></label>
    </div>
    <p class="xs faint">Both optional. Leave either empty to drop it.</p>
    <div class="actions"><button class="primary" type="submit">Save</button>
      <button type="button" class="quiet" data-act="unform" data-form="due:${t.id}">cancel</button>
    </div></form>`;
}

function splitForm(t, key) {
  return `<form class="panel" data-form="split" data-id="${t.id}">
    <label class="field"><span>This is bigger than one person. What is the group's goal?</span>
      <input name="goal" required autofocus value="${esc(t.title)}"></label>
    <p class="xs faint">${esc(t.owner_name || 'You')} will lead it. The work stops being
      counted here and its progress comes back up from the new cell.</p>
    <div class="actions"><button class="primary" type="submit">Split it off</button>
      <button type="button" class="quiet" data-act="unform" data-form="${key}">cancel</button>
    </div></form>`;
}

function work(v) {
  const live = v.tasks.filter((t) => t.state !== 'done');
  const done = v.tasks.filter((t) => t.state === 'done');
  return `<section><h2>Tasks</h2>
    ${v.tasks.length
      ? live.map((t) => taskRow(v, t)).join('') + finished(v, done)
      : '<p class="empty">Accepted decisions turn into tasks here on their own.</p>'}
    ${showing('task')
      ? `<form class="panel" data-form="task">
           <label class="field"><span>What needs doing?</span>
             <input name="title" required autofocus></label>
           <div class="actions"><button class="primary" type="submit">Add</button>
             <button type="button" class="quiet" data-act="unform" data-form="task">cancel</button>
           </div></form>`
      : (v.you.acts_here
          ? '<p><button data-act="form" data-form="task">Add a task</button></p>' : '')}
  </section>`;
}

function finished(v, done) {
  if (!done.length) return '';
  return showing('done')
    ? done.map((t) => taskRow(v, t)).join('') +
      '<p><button class="quiet faint" data-act="unform" data-form="done">hide what is done</button></p>'
    : `<p><button class="quiet faint" data-act="form" data-form="done">${
        plural(done.length, 'finished thing')}</button></p>`;
}

/* ------------------------------------------------------------------ mine */

/*
  The responsibility map. Not a dashboard: it answers what you are expected to
  accomplish, in the order a person actually asks -- what is mine, who is
  waiting on me, what am I waiting on, what is stuck.
*/
function yours(v) {
  if (!v.yours) return '';
  const y = v.yours;
  const waiting = y.waiting_on_you;
  const blocked = y.you_are_waiting_on;

  const lines = [];
  if (waiting.votes.length)
    lines.push(row('waiting', `${plural(waiting.votes.length, 'question')} waiting for your answer`,
                   waiting.votes));
  if (waiting.decisions.length)
    lines.push(row('waiting', `${plural(waiting.decisions.length, 'question')} only you can settle`,
                   waiting.decisions));
  if (waiting.not_started.length)
    lines.push(row('waiting', `${plural(waiting.not_started.length, 'thing')} you hold but have not started`));
  if (blocked.work.length)
    lines.push(row('', `${plural(blocked.work.length, 'thing')} you are waiting on other people for`));
  if (y.blocked.length)
    lines.push(row('stuck', `${plural(y.blocked.length, 'thing')} nobody has taken`));
  if (y.moving.length)
    lines.push(row('', `${plural(y.moving.length, 'thing')} moving`));

  return `<section><h2>Yours</h2>
    ${lines.join('')}
    ${y.yours.length
      ? y.yours.map((t) => taskRow(v, t)).join('') +
        `<p class="xs faint">${y.progress.percent}% across ${plural(y.yours.length, 'thing')}</p>`
      : '<p class="empty">Nothing assigned to you here.</p>'}
    ${y.cells_led.length
      ? `<p class="xs faint">You lead ${plural(y.cells_led.length, 'cell')} here.</p>` : ''}
  </section>`;
}

const row = (tone, text, questions) => `<div class="carried ${tone}">
  <span>${esc(text)}</span>
  ${(questions || []).map((q) => `<button class="quiet" data-act="open"
      data-cell="${q.cell_id}">${esc(q.question)}</button>`).join('')}
</div>`;

/*
  What this cell grew out of. A cell that began as a piece of work carries
  that work as its mission, with everything already attached to it -- nothing
  was copied here, it is the same task read from where it always was.
*/
function mission(v) {
  if (!v.mission) return '';
  const m = v.mission;
  return `<section class="mission"><h2>Mission</h2>
    <p class="q">${esc(m.title)}</p>
    <p class="xs faint">grew out of work in
      <button class="quiet" data-act="open" data-cell="${m.from_cell.id}">${esc(m.from_cell.goal)}</button>
      ${m.decision ? ` · asked as “${esc(m.decision.question)}”` : ''}</p>
    ${m.evidence.length
      ? `<div class="evidence stack">${m.evidence.map((e) => `<div class="row sm">
          <span class="kind">${esc(e.kind)}</span>
          ${e.ref ? `<a href="${esc(e.ref)}" target="_blank" rel="noopener">${esc(e.label)}</a>`
                  : `<span>${esc(e.label)}</span>`}</div>`).join('')}</div>`
      : ''}
  </section>`;
}

/* -------------------------------------------------------------- hierarchy */

function inside(v) {
  if (!('structure' in v)) return '';
  return `<section><h2>Inside</h2>
    ${v.structure
      ? mapMount() + mapCaption(v.structure)
      : '<p class="empty">No cells inside this one yet.</p>'}
    ${showing('child')
      ? `<form class="panel" data-form="child">
           <label class="field"><span>What is that group's goal?</span>
             <input name="goal" required autofocus></label>
           <p class="xs faint">It becomes a piece of work, and that work expands
             into a cell — the same path as splitting something too large.</p>
           <div class="actions"><button class="primary" type="submit">Create</button>
             <button type="button" class="quiet" data-act="unform" data-form="child">cancel</button>
           </div></form>`
      : (v.you.can_create_child
          ? '<p><button data-act="form" data-form="child">Start a group inside this one</button></p>' : '')}
  </section>`;
}

/* ------------------------------------------------------------- analytics */

function analytics(v) {
  if (!v.analytics) return '';
  const a = v.analytics;
  const tiles = [
    [a.people, 'people'],
    [a.cells, 'cells'],
    [a.decisions, 'decisions'],
    [a.override_rate + '%', 'resolved against the vote'],
    [a.knowledge_recorded, 'outcomes recorded'],
    [a.evidence, 'pieces of evidence'],
    [a.work.remaining, 'tasks left'],
    [a.unowned_tasks, 'tasks nobody owns'],
    [a.stalled_tasks, 'taken but not started'],
  ];
  return `<section><h2>Analytics</h2><div class="stats">
    ${tiles.map(([n, label]) => `<div class="stat"><b>${n}</b><span>${label}</span></div>`).join('')}
  </div></section>`;
}

/* ---------------------------------------------------------------- settled */

function settled(v) {
  if (!v.settled_decisions.length) return '';
  return `<section><h2>Answered</h2>
    ${v.settled_decisions.map((d) => card(v, d)).join('')}</section>`;
}

function knowledge(v) {
  if (!v.knowledge) return '';
  return `<section><h2>What we know</h2>
    ${v.knowledge.map((k) => `<div class="know">
      <div class="q">${esc(k.question)}</div>
      <div class="sm muted">${esc(k.outcome)}</div>
      ${k.lesson ? `<div class="lesson">${esc(k.lesson)}</div>` : ''}
      <div class="xs faint" style="margin-top:var(--s1)">
        ${esc(k.decided_by_name || 'someone')} · ${esc(k.cell_goal)}</div>
    </div>`).join('')}</section>`;
}

function record(v) {
  return `<section><h2>What has happened here</h2>
    ${S.log
      ? `<div class="log">${S.log.map((e) => `
          <div><time>${esc(when(e.occurred_at))}</time><span>${esc(happened(e))}</span></div>`
        ).join('')}</div>
         <p><button class="quiet faint" data-act="hidelog">hide</button></p>`
      : '<p><button data-act="showlog">Show the record</button></p>'}
  </section>`;
}
