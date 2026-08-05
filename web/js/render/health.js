/*
  Health, as one circle beside the goal.

  A cell's health is a diagnosis, not work: it is worth a glance and almost
  never worth a section. So it sits next to the title as a single dot coloured
  by how the cell is doing, and everything behind that judgement -- what is in
  the way, whether it is improving, and the three bars it was derived from --
  appears when you reach for it.

  Nothing here computes anything. Potential, friction, capacity and momentum
  all arrived from the server, derived from facts nobody typed in.
*/

import { esc, plural } from '../dom.js';
import { HEALTH_WORD, MOMENTUM_WORD } from '../labels.js';
import { showing } from '../store.js';

const SCALE = 100;

export function pip(v) {
  const h = v.health;
  if (!h) return '';

  const band = h.health.replace(' ', '-');
  const open = showing('health');
  const word = HEALTH_WORD[h.health] || h.health;

  return `<button class="pip ${band}${open ? ' open' : ''}"
    data-act="${open ? 'unform' : 'form'}" data-form="health"
    aria-label="Health: ${esc(word)}. ${esc(h.attention_count
      ? plural(h.attention_count, 'thing') + ' need attention' : 'Nothing needs attention')}.">
    <span class="dot"></span>
    <span class="reading">
      <span class="verdict-line">
        <b>${esc(word)}</b>
        <span class="xs faint">${esc(MOMENTUM_WORD[h.momentum] || '')}</span>
      </span>
      ${h.attention.length
        ? `<span class="attention">${h.attention.map((a) => `<span>${esc(a)}</span>`).join('')}${
            h.attention_count > h.attention.length
              ? `<span class="xs faint">and ${plural(
                   h.attention_count - h.attention.length, 'other thing')}</span>` : ''}</span>`
        : '<span class="xs faint">Nothing needs attention.</span>'}
      ${bars(h)}
    </span>
  </button>`;
}

function bars(h) {
  return `<span class="bars">
    ${bar('Potential', h.potential, 'what this cell could do')}
    ${bar('Friction', h.friction, 'what is in the way', true)}
    ${bar('Capacity', h.capacity, 'what it can do right now')}
  </span>`;
}

function bar(label, value, hint, warm) {
  const width = Math.round((Math.max(0, Math.min(SCALE, value)) / SCALE) * 100);
  return `<span class="bar-row">
    <span class="bar-label">${esc(label)}</span>
    <span class="bar${warm ? ' warm' : ''}"><i style="width:${width}%"></i></span>
    <span class="xs faint">${esc(hint)}</span>
  </span>`;
}
