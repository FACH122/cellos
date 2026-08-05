/*
  Health.

  A word, and the two or three things currently in the way. The bars are
  behind a click because most of the time the word and the attention list are
  the whole answer -- and because a person who cannot change a number should
  not be shown one.

  Nothing here computes anything. Potential, friction, capacity and momentum
  all arrived from the server, derived from facts nobody typed in.
*/

import { esc, plural } from '../dom.js';
import { HEALTH_WORD, MOMENTUM_WORD } from '../labels.js';
import { showing } from '../store.js';

const SCALE = 100;

export function health(v) {
  const h = v.health;
  if (!h) return '';

  return `<section><h2>Health</h2>
    <div class="verdict ${esc(h.health.replace(' ', '-'))}">
      <b>${esc(HEALTH_WORD[h.health] || h.health)}</b>
      <span class="xs faint">${esc(MOMENTUM_WORD[h.momentum] || '')}</span>
      ${showing('health')
        ? '<button class="quiet faint" data-act="unform" data-form="health">less</button>'
        : '<button class="quiet faint" data-act="form" data-form="health">why</button>'}
    </div>

    ${showing('health') ? bars(h) : ''}

    ${h.attention.length
      ? `<div class="attention">
           ${h.attention.map((a) => `<div>${esc(a)}</div>`).join('')}
           ${h.attention_count > h.attention.length
             ? `<div class="xs faint">and ${plural(
                  h.attention_count - h.attention.length, 'other thing')}</div>` : ''}
         </div>`
      : '<p class="xs faint">Nothing needs attention.</p>'}
  </section>`;
}

function bars(h) {
  return `<div class="bars">
    ${bar('Potential', h.potential, 'what this cell could do')}
    ${bar('Friction', h.friction, 'what is in the way', true)}
    ${bar('Capacity', h.capacity, 'what it can actually do right now')}
  </div>`;
}

function bar(label, value, hint, warm) {
  const width = Math.round((Math.max(0, Math.min(SCALE, value)) / SCALE) * 100);
  return `<div class="bar-row">
    <span class="bar-label">${esc(label)}</span>
    <span class="bar${warm ? ' warm' : ''}"><i style="width:${width}%"></i></span>
    <span class="xs faint">${esc(hint)}</span>
  </div>`;
}
