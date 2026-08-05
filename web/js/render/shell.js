/* Sign-in, the list of cells a person belongs to, and the header. */

import { esc, meter, plural, shorten } from '../dom.js';
import { S, showing } from '../store.js';

export function entry() {
  return `<div class="entry">
    <h1>CellOS</h1>
    <p>A goal, the people on it, what is still undecided, and what is being done.</p>
    <form data-form="signin">
      <label class="field"><span>Your name</span><input name="name" required autofocus></label>
      <label class="field"><span>Your email</span><input name="email" type="email" required></label>
      <button class="primary" type="submit">Continue</button>
    </form>
    <p class="xs faint" style="margin-top:var(--s5)">
      No password. This is a local system; anyone who can reach it can sign in as anyone.</p>
  </div>`;
}

export function homePage(v) {
  return `<section style="margin-top:var(--s7)">
    <h1>${v.cells.length ? 'What you are part of' : 'Nothing yet'}</h1>
    ${v.cells.length
      ? v.cells.map((c) => `
          <div class="child" data-act="open" data-cell="${c.id}">
            <span class="goal">${esc(c.goal)}</span>
            <span class="xs faint">${c.people === 1 ? 'just you'
              : plural(c.people, 'person', 'people')}</span>
            ${c.open_decisions
              ? `<span class="xs" style="color:var(--warn)">${
                  plural(c.open_decisions, 'open decision')}</span>` : ''}
            ${meter(c.percent)}
            <span class="xs faint" style="width:2.5rem;text-align:right">${c.percent}%</span>
          </div>`).join('')
      : `<p class="muted">Start with one goal and the people on it.
         Everything else appears when you need it.</p>`}
    ${showing('start')
      ? `<form class="panel" data-form="cell">
           <label class="field"><span>What is the goal?</span>
             <input name="goal" required autofocus placeholder="Plan the wedding"></label>
           <div class="actions"><button class="primary" type="submit">Create</button>
             <button type="button" class="quiet" data-act="unform" data-form="start">cancel</button>
           </div></form>`
      : `<p style="margin-top:var(--s6)">
           <button data-act="form" data-form="start">Start something</button></p>`}
  </section>`;
}

export function crumbs() {
  if (!S.cellId || !S.view || !S.view.path) return '<span class="here">CellOS</span>';
  const parts = ['<span class="crumb" data-act="home">CellOS</span>'];
  S.view.path.forEach((p, i) => {
    const last = i === S.view.path.length - 1;
    parts.push('<span class="sep">/</span>');
    parts.push(last
      ? `<span class="here">${esc(shorten(p.goal))}</span>`
      : `<span class="crumb" data-act="open" data-cell="${p.id}">${esc(shorten(p.goal))}</span>`);
  });
  return parts.join(' ');
}
