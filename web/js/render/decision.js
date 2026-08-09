/*
  A decision card.

  Every button on it comes from `d.actions`, which the workflow engine
  produced, and every form comes from that action's `asks`. This file decides
  nothing about what is allowed, what comes next, or who may do it.
*/

import { esc, meter, plural } from '../dom.js';
import { expectation } from '../labels.js';
import { S, showing } from '../store.js';

export function card(view, d) {
  const open = S.open.has(d.id);
  /* When the question is waiting on this particular person, say that rather
     than naming the state it happens to be in. */
  const [said, tone] = expectation(d);
  return `<div class="card">
    <div class="head" data-act="expand" data-id="${d.id}">
      <span class="q">${esc(d.question)}</span>
      <span class="stage ${tone}">${esc(said)}</span>
    </div>
    ${open ? body(view, d) : rail(d)}
  </div>`;
}

function rail(d) {
  if (d.position === null || d.position === undefined) return '';
  let dots = '';
  for (let i = 0; i < d.lifecycle_length; i++) {
    dots += `<i class="${i < d.position ? 'past' : i === d.position ? 'now' : ''}"></i>`;
  }
  return `<div class="rail">${dots}<span>${d.turnout ? plural(d.turnout, 'vote') : ''}</span></div>`;
}

function body(view, d) {
  const parts = [];

  if (d.detail) parts.push(`<p class="muted">${esc(d.detail)}</p>`);

  if (d.revision_note) {
    parts.push(`<div class="notice">
      <b>Sent back for rework.</b> ${esc(d.revision_note)}</div>`);
  }

  parts.push(options(d));

  if (d.decided_by_name) parts.push(verdict(d));
  if (d.remarks.length || d.actions.length) parts.push(discussion(view, d));
  if (view.evidence_in_use || d.evidence.length) parts.push(evidence(view, d));
  if (d.tasks.length) parts.push(work(d));
  if (d.outcome) parts.push(outcome(d));

  parts.push(actions(d));
  return `<div class="body">${parts.join('')}</div>`;
}

/*
  The options.

  They were filled boxes stacked inside a filled card, which is a box in a box
  and reads as clutter however carefully the greys are chosen. They are rows
  now, separated by a hairline, with the share of the vote drawn as a tint
  running behind the text -- so the distribution is legible at a glance
  instead of being four numbers you have to compare yourself.
*/
function options(d) {
  const votable = d.state === 'voting' && d.can_vote;
  return `<ul class="options">` + d.options.map((o) => {
    const share = d.turnout ? Math.round((o.votes / d.turnout) * 100) : 0;
    const classes = ['option',
      votable ? 'votable' : '',
      d.your_vote === o.id ? 'yours' : '',
      o.chosen ? 'chosen' : ''].filter(Boolean).join(' ');
    return `<li class="${classes}"
      ${votable ? `role="button" tabindex="0" data-act="vote" data-id="${d.id}"
                   data-option="${o.id}"` : ''}>
      ${share ? `<span class="fill" style="width:${share}%" aria-hidden="true"></span>` : ''}
      <span class="txt">${esc(o.text)}${
        d.your_vote === o.id ? '<span class="mine">your answer</span>' : ''}${
        o.chosen ? '<span class="mine">chosen</span>' : ''}
        ${o.work.length
          ? `<span class="work">then: ${o.work.map(esc).join(' · ')}</span>` : ''}
      </span>
      ${d.turnout ? `<span class="count">${o.votes || 0}</span>` : ''}
    </li>`;
  }).join('') + '</ul>';
}

function verdict(d) {
  if (d.decided_how === 'override') {
    return `<div class="notice">
      <b>${esc(d.decided_by_name)} decided against the vote.</b>
      <div style="margin-top:var(--s1)">${esc(d.resolution_note)}</div></div>`;
  }
  const what = d.decided_how === 'vote' ? 'confirmed the vote' : 'decided this';
  return `<p class="sm muted">${esc(d.decided_by_name)} ${what}${
    d.resolution_note ? ' — ' + esc(d.resolution_note) : '.'}</p>`;
}

function discussion(view, d) {
  const said = d.remarks.map((r) => `<div class="said">
    <b>${esc(r.author_name || 'someone')}</b> ${esc(r.body)}</div>`).join('');
  const canSpeak = view.you.acts_here && d.actions.length;
  return `<div>${said}
    ${canSpeak ? `<form data-form="remark" data-id="${d.id}" class="row" style="margin-top:var(--s3)">
        <input name="body" placeholder="Say something" class="grow">
        <button type="submit">Add</button></form>` : ''}
  </div>`;
}

function evidence(view, d) {
  const key = 'ev:' + d.id;
  const listed = d.evidence.map((e) => `<div class="row sm">
    <span class="kind">${esc(e.kind)}</span>
    ${e.ref ? `<a href="${esc(e.ref)}" target="_blank" rel="noopener">${esc(e.label)}</a>`
            : `<span>${esc(e.label)}</span>`}
    <span class="xs faint">${esc(e.added_by_name || '')}</span></div>`).join('');

  return `<div class="evidence stack">${listed}
    ${showing(key)
      ? `<form data-form="evidence" data-id="${d.id}" class="stack" style="margin-top:var(--s2)">
           <div class="row">
             <select name="kind" style="width:9rem">
               ${['link', 'file', 'document', 'measurement', 'report', 'note']
                 .map((k) => `<option>${k}</option>`).join('')}
             </select>
             <input name="label" placeholder="What is it?" class="grow" required autofocus>
           </div>
           <div class="row">
             <input name="ref" placeholder="Link or reference (optional)" class="grow">
             <button class="primary" type="submit">Attach</button>
             <button type="button" class="quiet" data-act="unform" data-form="${key}">cancel</button>
           </div>
         </form>`
      : (view.you.acts_here
          ? `<p><button class="quiet faint" data-act="form" data-form="${key}">+ evidence</button></p>`
          : '')}
  </div>`;
}

function work(d) {
  return `<div>
    <div class="xs faint" style="margin-bottom:var(--s1)">This became:</div>
    ${d.tasks.map((t) => `<div class="task${t.state === 'done' ? ' done' : ''}">
      <span class="title">${esc(t.title)}</span>
      <span class="owner">${esc(t.owner_name || 'nobody yet')}</span>
      <span class="pct">${t.progress}%</span></div>`).join('')}
  </div>`;
}

function outcome(d) {
  return `<div class="notice calm">
    <b>How it turned out.</b> ${esc(d.outcome)}
    ${d.lesson ? `<div style="margin-top:var(--s1)">${esc(d.lesson)}</div>` : ''}</div>`;
}

/* ---------------------------------------------------------------- actions */

function actions(d) {
  if (!d.actions.length) return '';

  const simple = d.actions.filter((a) => !a.asks.length);
  const asking = d.actions.filter((a) => a.asks.length);
  /* The workflow says which steps carry the question forward and which step
     out of it. Four buttons of equal weight said nothing about what to do
     next; now the first onward step is the filled one and the rest recede. */
  const offered = [
    ...simple,
    ...asking.filter((a) => !showing(formKey(d, a))),
  ];
  const lead = offered.find((a) => a.tone !== 'aside');
  const buttons = offered
    .map((a) => button(d, a, a === lead ? 'primary' : a.tone === 'aside' ? 'quiet' : ''))
    .join(' ');

  const forms = asking
    .filter((a) => showing(formKey(d, a)))
    .map((a) => stepForm(d, a))
    .join('');

  return (buttons ? `<div class="row wrap">${buttons}</div>` : '') + forms;
}

const formKey = (d, a) => `step:${a.name}:${d.id}`;

/*
  The caller decides the weight, because only it knows which of the offered
  steps is the one in front. Declining is still drawn as a caution wherever it
  appears -- that is about the step itself, not about where it sits in a list.
*/
function button(d, a, weight) {
  const tone = a.target === 'rejected' ? 'quiet caution' : weight;
  return a.asks.length
    ? `<button class="${tone}" data-act="form" data-form="${formKey(d, a)}">${esc(a.label)}</button>`
    : `<button class="${tone}" data-act="step" data-id="${d.id}" data-step="${a.name}">${esc(a.label)}</button>`;
}

/* Built from what the transition says it needs, not from what it is called. */
function stepForm(d, a) {
  const fields = a.asks.map((ask) => {
    if (ask.kind === 'option') {
      return `<label class="field"><span>${esc(ask.label)}</span>
        <select name="${ask.name}">${d.options.map(
          (o) => `<option value="${o.id}">${esc(o.text)}</option>`).join('')}</select></label>`;
    }
    const control = ask.kind === 'line'
      ? `<input name="${ask.name}" ${ask.required ? 'required autofocus' : ''}>`
      : `<textarea name="${ask.name}" ${ask.required ? 'required' : ''}
           placeholder="${esc(ask.hint || '')}"></textarea>`;
    return `<label class="field"><span>${esc(ask.label)}</span>${control}</label>`;
  }).join('');

  return `<form class="panel" data-form="step" data-id="${d.id}" data-step="${a.name}">
    ${fields}
    <div class="actions">
      <button class="primary" type="submit">${esc(a.label)}</button>
      <button type="button" class="quiet" data-act="unform" data-form="${formKey(d, a)}">cancel</button>
    </div></form>`;
}
