/* Rendering helpers. No knowledge of CellOS at all. */

export const esc = (s) => String(s == null ? '' : s).replace(
  /[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + 's')}`;

export const when = (iso) => {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' ' +
         d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
};

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
