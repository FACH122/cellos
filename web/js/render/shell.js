/* Sign-in, the list of cells a person belongs to, the map on its own, and the header. */

import { CELL_MARK, esc, meter, plural, shorten } from '../dom.js';
import { S, showing } from '../store.js';
import { mapCaption, mapMount } from './structure.js';

export function entry() {
  return `<div class="entry">
    <h1>CellOS</h1>
    <p>A goal, the people on it, what is still undecided, and what is being done.</p>
    <form data-form="signin">
      <label class="field"><span>Your name</span>
        <input name="name" required autofocus placeholder="Marisol Vega"></label>
      <label class="field"><span>Your email</span>
        <input name="email" type="email" required placeholder="marisol.vega@gmail.com"></label>
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
            <span class="goal">${CELL_MARK}${esc(c.goal)}</span>
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
           <button class="add" data-act="form" data-form="start">Start something</button></p>`}
  </section>`;
}

/*
  The map with the page to itself.

  Nothing here is new: it is the same map object, with the same branches open,
  moved into a mount that gives it the whole window instead of a column. A
  cell nested eight deep is a legitimate thing to want to look at, and there
  is no arrangement of a 62rem column that makes that comfortable.

  Clicking a cell still goes to that cell -- which means leaving this page for
  that cell's own, because going somewhere is what clicking a cell has always
  meant here.
*/
export function mapPage(v) {
  if (!v.structure) {
    return `<section style="margin-top:var(--s7)">
      <h1 class="goal">${CELL_MARK}${esc(v.cell.goal)}</h1>
      <p class="muted">There are no cells inside this one yet, so there is no map to show.</p>
      <p><button data-act="unmap">Back to the cell</button></p>
    </section>`;
  }
  return `<section class="map-page">
    <div class="row top">
      <div class="grow">
        <h1 class="goal">${CELL_MARK}${esc(v.cell.goal)}</h1>
        <p class="xs faint">everything inside it</p>
      </div>
      <button class="quiet faint" data-act="unmap">back to the cell</button>
    </div>
    ${mapMount(true)}
    ${mapCaption(v.structure, true)}
  </section>`;
}

export function crumbs() {
  if (!S.cellId || !S.view || !S.view.path) return '<span class="here">CellOS</span>';
  const mapping = S.page === 'map';
  const onTask = S.page === 'task';
  const parts = ['<span class="crumb" data-act="home">CellOS</span>'];
  S.view.path.forEach((p, i) => {
    const last = i === S.view.path.length - 1 && !mapping && !onTask;
    parts.push('<span class="sep">/</span>');
    parts.push(last
      ? `<span class="here">${esc(shorten(p.goal))}</span>`
      : `<span class="crumb" data-act="open" data-cell="${p.id}">${esc(shorten(p.goal))}</span>`);
  });
  if (mapping) parts.push('<span class="sep">/</span>', '<span class="here">map</span>');
  if (onTask && S.view.task) {
    parts.push('<span class="sep">/</span>',
               `<span class="here">${esc(shorten(S.view.task.title))}</span>`);
  }
  return parts.join(' ');
}
