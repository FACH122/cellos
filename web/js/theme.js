/*
  Light or dark, or whichever the machine is using.

  Three states rather than two, because "follow my system" is the honest
  default and the one most people want -- but some rooms, some screens and
  some eyes need the choice made explicitly, and that is not a preference the
  operating system can know.

  The resolved answer is written to `data-theme` on the root element, so the
  stylesheet holds one palette per theme and no media query. A three-line
  script in the page head does the same thing before first paint, so there is
  never a flash of the wrong theme.
*/

const KEY = 'cellos.theme';
const ORDER = ['auto', 'light', 'dark'];

const systemIsDark = () =>
  window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

export const preference = () => {
  const saved = localStorage.getItem(KEY);
  return ORDER.includes(saved) ? saved : 'auto';
};

const resolve = (pref) => (pref === 'auto' ? (systemIsDark() ? 'dark' : 'light') : pref);

export function apply(pref = preference()) {
  document.documentElement.dataset.theme = resolve(pref);
}

/* One quiet control, so cycling is the whole interaction. */
export function cycle() {
  const next = ORDER[(ORDER.indexOf(preference()) + 1) % ORDER.length];
  localStorage.setItem(KEY, next);
  apply(next);
  return next;
}

export function label() {
  const pref = preference();
  return pref === 'auto' ? `auto · ${resolve(pref)}` : pref;
}

export function describe() {
  const pref = preference();
  const next = ORDER[(ORDER.indexOf(pref) + 1) % ORDER.length];
  const now = pref === 'auto'
    ? `Following your system, which is ${resolve(pref)} right now.`
    : `Always ${pref}.`;
  return `${now} Click for ${next === 'auto' ? 'your system setting' : next}.`;
}

/* While on auto, follow the machine if it changes under us. */
if (window.matchMedia) {
  const watch = window.matchMedia('(prefers-color-scheme: dark)');
  const follow = () => { if (preference() === 'auto') apply(); };
  watch.addEventListener ? watch.addEventListener('change', follow)
                         : watch.addListener(follow);
}
