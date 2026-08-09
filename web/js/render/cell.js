/*
  One cell.

  Every section below is drawn only if the server sent the key it needs. A
  two-person cell is not sent a dashboard, so there is no branch here that
  hides one -- there is simply nothing to draw.
*/

import { CELL_MARK, TASK_MARK, esc, meter, plural, when } from '../dom.js';
import { happened } from '../labels.js';
import { S, showing } from '../store.js';

import { card } from './decision.js';
import { mapMount, mapCaption } from './structure.js';
import { pip } from './health.js';

/*
  How many names to show before the list stops being a list.

  Below COMFORTABLE, a cell is a group whose members you know, and the names
  are worth reading -- so all of them appear and there is nothing to expand.
  Above it, "who are these people" stops being a question anybody asks; the
  ones that matter are whoever leads, and the rest is a number -- and that
  number is already in the line under the goal.

  Three names, then the count. The server sorts leaders first, so the front
  of the list is the part worth reading, and three of them still leaves the
  section one line tall.
*/
const COMFORTABLE = 8;
const ANSWERED_AT_REST = 3;
const AT_A_GLANCE = 3;

export function cellPage(v) {
  return [
    goal(v),
    mission(v),
    people(v),
    questions(v),
    work(v),
    inside(v),
    analytics(v),
    more(v),
  ].filter(Boolean).join('');
}

/*
  The line under everything a person can act on.

  Everything behind it is the past: what the cell has learned, the decisions
  it has already made, and the log of what has happened here. All three are
  worth keeping and none is worth the height it was taking on a page somebody
  opens to find out what to do next.

  They come out in order of how much has been made of them -- a lesson, then
  the decisions it came from, then the raw record -- so the most digested
  thing is the first one you meet.

  The control does not move when it opens, so the sections appear below it
  rather than pushing it down the page.
*/
function more(v) {
  const open = showing('more');
  const behind = open ? knowledge(v) + settled(v) + record(v) : '';
  return `<section class="more">
    <button class="quiet faint" data-act="${open ? 'unform' : 'form'}" data-form="more"
      aria-label="What we know, decisions already made, and what has happened here"
      aria-expanded="${open}">${open ? 'less' : 'more'}</button>
  </section>${behind}`;
}

/* ------------------------------------------------------------------ goal */

function goal(v) {
  const p = v.progress;
  return `<section>
    <div class="row top titled"><h1 class="goal grow">${CELL_MARK}${esc(v.cell.goal)}</h1></div>
    <div class="pulse">
      ${pip(v)}
      <span>${v.scale === 1 ? 'just you' : plural(v.scale, 'person', 'people')}</span>
      ${p.task_count
        ? `<span>${meter(p.percent)} ${p.percent}%</span>
           <span class="faint">${p.remaining
             ? plural(p.remaining, 'thing') + ' left' : 'everything done'}</span>`
        : '<span class="faint">nothing being done yet</span>'}
      ${cellMarks(v)}
    </div>
    ${money(v)}
    ${showing('budget') ? commitmentForm(v) : ''}
  </section>`;
}


/*
  Where this cell's money sits in the tree.

  A budget on its own is a number a group typed in. What makes it mean
  anything is the two facts either side of it: how much of it the cells inside
  have already claimed, and whose money it was in the first place. Both are
  read off the tree on every request; neither is stored.

  Nothing here refuses anything. A cell whose children have promised more than
  it holds is told so, in the same voice as a task that is late.
*/
function money(v) {
  const k = v.constraints || {};
  const b = k.budget;
  const from = k.drawn_from;
  const lines = [];

  if (b && b.allocated) {
    lines.push(`<span class="${b.over_allocated ? 'warn-text' : 'faint'}">${
      b.over_allocated ? 'the cells inside have committed to more than this cell has —' : ''
      } ${esc(String(b.allocated_to))} ${b.allocated_to === 1 ? 'cell inside holds' : 'cells inside hold'
      } ${esc(reads(b.allocated, b.currency))} of it</span>`);
  }
  if (from) {
    lines.push(`<span class="faint">${from.reads ? esc(from.reads) + ' committed by' : 'inside'}
      <button class="quiet" data-act="open" data-cell="${from.cell_id}">${esc(from.goal)}</button>${
      from.currencies_differ ? ' <span class="warn-text">— different currencies</span>' : ''}</span>`);
  }
  return lines.length ? `<p class="xs subtle-money">${lines.join(' · ')}</p>` : '';
}

const reads = (amount, currency) =>
  `${currency || ''} ${Math.round(amount).toLocaleString('en-US')}`;

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
    <label class="field"><span>The goal</span>
      <input name="goal" required autofocus value="${esc(v.cell.goal)}"></label>
    <div class="row">
      <label class="field grow"><span>What is this cell willing to spend?</span>
        <input name="amount" inputmode="decimal"
               value="${b.amount === undefined ? '' : b.amount}"
               placeholder="leave empty for no budget"></label>
      <label class="field" style="width:6rem"><span>Currency</span>
        <input name="currency" value="${esc(b.currency || 'EUR')}"></label>
      <label class="field grow"><span>Wanted by</span>
        <input name="due_on" type="date" value="${esc(d.due_on || '')}"></label>
    </div>
    <p class="xs faint">Both optional. Spending is the sum of what the work cost,
      rolled up from the cells inside.${b.allocated
        ? ` The cells inside this one have already committed to
            ${esc(reads(b.allocated, b.currency))}${b.unallocated >= 0
              ? `, leaving ${esc(reads(b.unallocated, b.currency))} of this budget unclaimed`
              : ''}.` : ''}${(v.constraints && v.constraints.drawn_from)
        ? ` This cell's budget is part of ${esc(v.constraints.drawn_from.goal)}'s.` : ''}
      Nothing is enforced — CellOS will say when the money is close, when the date
      has passed, or when the cells inside have promised more than there is.</p>
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

  return `<section class="aside"><h2>People</h2>
    <div class="people">
      ${shown.map((m) => `<span class="chip${m.id === S.user.id ? ' you' : ''}">${esc(m.name)}${
        m.role === 'leader' ? '<span class="tag">leads</span>' : ''}</span>`).join('')}
      ${hidden
        ? `<button class="quiet faint" data-act="form" data-form="people">and ${hidden} more</button>`
        : ''}
      ${!small && showing('people')
        ? '<button class="quiet faint" data-act="unform" data-form="people">show fewer</button>' : ''}
      ${v.you.can_admit && !showing('member')
        ? '<button class="quiet faint" data-act="form" data-form="member">bring someone in</button>'
        : ''}
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
      : ''}
  </section>`;
}

/* ------------------------------------------------------------- decisions */

function questions(v) {
  return `<section><h2>Open decisions</h2>
    ${v.open_decisions.length
      ? v.open_decisions.map((d) => card(v, d)).join('')
      : '<p class="empty">Nothing waiting on anyone.</p>'}
    ${showing('decision')
      ? proposeForm()
      : (v.you.acts_here
          ? '<p><button data-act="form" data-form="decision">Ask the cell something</button></p>' : '')}
  </section>`;
}

/*
  Every option gets to say what follows from it.

  The form used to take the options as free lines and then ask, once, what
  should happen "if the first option wins" -- which was never a rule, only the
  shape of the form. The domain has always kept work per option, and a
  question where you can only say the consequences of one answer is not really
  offering a choice: the other options arrive at the vote with nothing
  attached, and settling on one of them produces nothing.

  So one row per option, each with its own consequences, and a quiet way to
  add another.
*/
function optionRows() {
  const rows = [];
  for (let i = 0; i < S.optionRows; i += 1) {
    rows.push(`<div class="opt-row">
      <label class="field"><span>${i === 0 ? 'The options' : ''}</span>
        <input name="option${i}" placeholder="${
          i === 0 ? 'The garden' : i === 1 ? 'The hall' : 'another answer'}"></label>
      <label class="field"><span>${i === 0 ? 'then, one per line' : ''}</span>
        <textarea name="work${i}" rows="2" placeholder="${
          i === 0 ? 'Put down the deposit&#10;Confirm the date' : ''}"></textarea></label>
    </div>`);
  }
  return `<div class="opt-rows">${rows.join('')}
    ${S.optionRows < 6
      ? '<button type="button" class="quiet faint" data-act="moreoption">another option</button>'
      : ''}
    <p class="xs faint">All optional. A question with no options at all is just
      “shall we do this?”, and becomes one.</p>
  </div>`;
}

function proposeForm() {
  return `<form class="panel" data-form="decision">
    <label class="field"><span>What has to be decided together?</span>
      <input name="question" required autofocus placeholder="Where do we hold it?"></label>
    <label class="field"><span>Anything worth knowing first (optional)</span>
      <textarea name="detail"></textarea></label>
    ${optionRows()}
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
      <span class="title">${CELL_MARK}${esc(t.title)}
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
  /* A real link, so the browser's own ways of opening things all work:
     click, middle-click, cmd-click, copy the address. It cannot wrap the
     whole row -- there are buttons and a slider in there, and an anchor may
     not contain them -- so the title is the link. */
  return `<div class="task${t.state === 'done' ? ' done' : ''}">
    <a class="title" href="#task/${t.id}" target="_blank" rel="noopener"
       >${TASK_MARK}${esc(t.title)}</a>
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
    ${taskMarks(t)}
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
  What something has committed to, and the way in to changing it -- in one
  control, wherever it appears. On a task it holds a date and a cost; on the
  cell it holds a budget and a date. When there is nothing yet it shrinks to
  three faint characters rather than taking a line of its own, and it says
  what it will do when you reach for it.
*/
function marks({ bits, form, editable, add, change }) {
  const shown = bits.filter(Boolean);
  if (!editable) return shown.join('');
  const label = shown.length ? change : add;
  return `<button class="marks" data-act="form" data-form="${form}" aria-label="${esc(label)}">
    ${shown.length ? shown.join('') : '<span class="ellipsis">···</span>'}
    <span class="says">${esc(label.toLowerCase())}</span>
  </button>`;
}

function taskMarks(t) {
  if (t.state === 'expanded') return '';
  return marks({
    bits: [
      t.due_on && t.state !== 'done' ? dueMarker(t.due_on, t.days_left) : '',
      t.cost ? `<span class="due calm">${esc(String(t.cost))}</span>` : '',
    ],
    form: 'due:' + t.id,
    editable: t.can_time,
    add: 'Add a date or a cost',
    change: 'Change the date or cost',
  });
}

function cellMarks(v) {
  const k = v.constraints || {};
  return marks({
    bits: [
      k.budget ? `<span class="due ${k.budget.over ? 'late' : 'calm'}">${
        esc(k.budget.reads)}</span>` : '',
      k.due ? dueMarker(k.due.due_on, k.due.days_left) : '',
    ],
    form: 'budget',
    editable: v.you.is_leader,
    /* One control for everything a leader can change about the cell itself:
       what it is for, and what it has committed to. They were two, and the
       second one was a button sitting next to the title saying "edit" -- a
       word that tells you nothing about what it edits. */
    add: 'Edit this cell',
    change: 'Edit this cell',
  });
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
/* -------------------------------------------------------------- mission */

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
  const all = showing('answered');
  const shown = all ? v.settled_decisions : v.settled_decisions.slice(0, ANSWERED_AT_REST);
  const hidden = v.settled_decisions.length - shown.length;

  return `<section class="aside"><h2>Decisions made</h2>
    ${shown.map((d) => card(v, d)).join('')}
    ${hidden
      ? `<p><button class="quiet faint" data-act="form" data-form="answered">${
          plural(hidden, 'earlier decision')}</button></p>`
      : (all && v.settled_decisions.length > ANSWERED_AT_REST
          ? '<p><button class="quiet faint" data-act="unform" data-form="answered">show fewer</button></p>'
          : '')}
  </section>`;
}

function knowledge(v) {
  if (!v.knowledge) return '';
  return `<section class="aside"><h2>What we know</h2>
    ${v.knowledge.map((k) => `<div class="know">
      <div class="q">${esc(k.question)}</div>
      <div class="sm muted">${esc(k.outcome)}</div>
      ${k.lesson ? `<div class="lesson">${esc(k.lesson)}</div>` : ''}
      <div class="xs faint" style="margin-top:var(--s1)">
        ${esc(k.decided_by_name || 'someone')} · ${esc(k.cell_goal)}</div>
    </div>`).join('')}</section>`;
}

function record(v) {
  return `<section class="aside"><h2>What has happened here</h2>
    ${S.log
      ? `<div class="log">${S.log.map((e) => `
          <div><time>${esc(when(e.occurred_at))}</time><span>${esc(happened(e))}</span></div>`
        ).join('')}</div>
         <p><button class="quiet faint" data-act="hidelog">hide</button></p>`
      : '<p><button data-act="showlog">Show the record</button></p>'}
  </section>`;
}
