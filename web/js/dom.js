/* Rendering helpers. No knowledge of CellOS at all. */

export const esc = (s) => String(s == null ? '' : s).replace(
  /[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + 's')}`;

export const when = (iso) => {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' ' +
         d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
};

/*
  The two things the system is made of, given a mark each.

  A cell is a ◎ -- a ring with something alive inside it -- in gold, because a
  cell is what holds other things and what is worth going into. A task is a ○
  in cool metal: one plain thing somebody is carrying.

  The point is not the symbols. It is that after a minute nobody reads them
  and you simply know which kind of row you are looking at. Both are
  decorative and hidden from screen readers, which get the real words anyway.
*/
export const CELL_MARK = '<span class="glyph cell" aria-hidden="true">◎</span>';
export const TASK_MARK = '<span class="glyph task" aria-hidden="true">○</span>';

export const meter = (percent) =>
  `<span class="meter"><i style="width:${Number(percent) || 0}%"></i></span>`;

export const shorten = (s, n = 38) =>
  s.length > n ? s.slice(0, n - 2).trimEnd() + '…' : s;

const note = document.getElementById('note');
let timer;

export function say(text, bad) {
  note.textContent = text;
  note.className = bad ? 'bad' : '';
  note.hidden = false;
  clearTimeout(timer);
  timer = setTimeout(() => { note.hidden = true; }, bad ? 5200 : 2600);
}
