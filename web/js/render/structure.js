/*
  The structural map.

  Every circle is a cell. The ring around it is how far along it is; a dot on
  the rim means something in there needs attention, coloured by how the cell
  is doing. That is two things encoded, deliberately.

  Three things make this different from the rest of the interface, and all
  three follow from one requirement: **there is no maximum depth.**

  1. It is fetched as you go. A node knows how many cells are inside it; what
     they are is asked for when somebody opens it. Nothing is computed for a
     branch nobody has opened, so an organisation nested twenty deep costs
     exactly what you look at.

  2. It owns its own element and survives re-rendering. The rest of the page
     is rebuilt from a string on every action; this is not, because you cannot
     animate DOM you have thrown away.

  3. It moves rather than jumps. Positions are tweened, new cells grow out of
     their parent, collapsed ones fall back into it, and the view pans to
     follow what you opened.

  Still no library, still no build step: SVG, arithmetic and one animation
  frame loop.
*/

import { api } from '../api.js';
import { esc, plural } from '../dom.js';

const R = 17;            // node radius
const ROW = 96;          // vertical distance between levels
const GAP = 132;         // horizontal room per leaf
const PAD = 28;
const MS = 340;          // how long a rearrangement takes
const SVG_NS = 'http://www.w3.org/2000/svg';

let view = null;         // the one live map, kept across page re-renders
let onOpen = () => {};

export function whenOpened(fn) {
  onOpen = fn;
}

/*
  Called after every page render. Re-attaches the existing map if we are still
  in the same cell, so expansion state and positions survive; builds a fresh
  one if we moved.
*/
export function mountMap(mount, root) {
  if (!mount || !root) return;

  if (!view || view.rootId !== root.id) {
    view = build(root);
  } else {
    absorb(root);                       // same cell, fresher numbers
  }
  if (view.svg.parentNode !== mount) mount.appendChild(view.svg);
  view.mount = mount;
  draw(false);
}

export function forgetMap() {
  view = null;
}

/* ------------------------------------------------------------------ state */

function build(root) {
  const nodes = new Map();
  const kids = new Map();
  index(root, nodes, kids);

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'map');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'the cells inside this one');
  const edges = document.createElementNS(SVG_NS, 'g');
  edges.setAttribute('class', 'edges');
  svg.appendChild(edges);

  return {
    rootId: root.id, nodes, kids,
    expanded: new Set([root.id]),       // the root's own ring starts open
    drawn: new Map(),                   // id -> {g, x, y, from, to}
    edges, svg, mount: null, frame: null, pan: null,
  };
}

function index(node, nodes, kids) {
  nodes.set(node.id, node);
  if (node.children) {
    kids.set(node.id, node.children.map((c) => c.id));
    node.children.forEach((c) => index(c, nodes, kids));
  }
}

/* Same cell, new payload: refresh what we already show, keep what is open. */
function absorb(root) {
  const fresh = new Map();
  const freshKids = new Map();
  index(root, fresh, freshKids);
  fresh.forEach((n, id) => view.nodes.set(id, n));
  freshKids.forEach((v, k) => view.kids.set(k, v));
}

/* ----------------------------------------------------------------- layout */

/* Only what is open. This is what makes depth unbounded and cheap. */
function visible() {
  const out = [];
  const walk = (id, depth) => {
    const node = view.nodes.get(id);
    if (!node) return;
    out.push({ node, depth });
    if (view.expanded.has(id)) {
      (view.kids.get(id) || []).forEach((c) => walk(c, depth + 1));
    }
  };
  walk(view.rootId, 0);
  return out;
}

/*
  A leaf takes the next slot; a parent centres over its children. Laid out
  over the open set only, so the tree rebalances every time a branch opens or
  closes and never reserves room for something nobody is looking at.
*/
function layout() {
  const rows = visible();
  const place = new Map();
  let cursor = 0;

  const position = (id, depth) => {
    const children = view.expanded.has(id) ? (view.kids.get(id) || []) : [];
    const shown = children.filter((c) => view.nodes.has(c));
    if (!shown.length) {
      place.set(id, { x: cursor, y: PAD + R + depth * ROW });
      cursor += GAP;
      return;
    }
    shown.forEach((c) => position(c, depth + 1));
    const first = place.get(shown[0]).x;
    const last = place.get(shown[shown.length - 1]).x;
    place.set(id, { x: (first + last) / 2, y: PAD + R + depth * ROW });
  };
  position(view.rootId, 0);

  // Shift so the leftmost node sits at a sensible margin, with no dead space.
  const xs = [...place.values()].map((p) => p.x);
  const shift = -Math.min(...xs) + PAD + GAP / 2;
  place.forEach((p) => { p.x += shift; });

  const depth = Math.max(...rows.map((r) => r.depth));
  return {
    place,
    rows,
    width: Math.max(...xs) - Math.min(...xs) + PAD * 2 + GAP,
    height: depth * ROW + PAD * 2 + 52,
  };
}

/* ---------------------------------------------------------------- drawing */

function draw(animate = true) {
  const { place, rows, width, height } = layout();
  view.svg.setAttribute('viewBox', `0 0 ${Math.round(width)} ${Math.round(height)}`);
  view.svg.setAttribute('width', Math.round(width));
  view.svg.setAttribute('height', Math.round(height));

  const wanted = new Set(rows.map((r) => r.node.id));

  // Arrivals grow out of wherever their parent currently is.
  rows.forEach(({ node }) => {
    if (view.drawn.has(node.id)) return;
    const parent = parentOf(node.id);
    const born = (parent && view.drawn.get(parent))
      ? { x: view.drawn.get(parent).x, y: view.drawn.get(parent).y }
      : place.get(node.id);
    const g = nodeElement(node);
    view.svg.appendChild(g);
    view.drawn.set(node.id, { g, x: born.x, y: born.y, fading: 0 });
  });

  // Departures fall back into their parent and then go.
  view.drawn.forEach((d, id) => {
    if (wanted.has(id)) return;
    const parent = parentOf(id);
    const home = (parent && place.get(parent)) || place.get(view.rootId);
    d.fading = 1;
    d.to = { x: home.x, y: home.y };
  });

  rows.forEach(({ node }) => {
    const d = view.drawn.get(node.id);
    d.to = place.get(node.id);
    d.fading = 0;
    refresh(d.g, node);
  });

  tween(animate ? MS : 0);
}

function parentOf(id) {
  for (const [parent, list] of view.kids) if (list.includes(id)) return parent;
  return null;
}

const ease = (t) => 1 - Math.pow(1 - t, 3);

function tween(duration) {
  if (view.frame) cancelAnimationFrame(view.frame);
  const start = performance.now();
  const from = new Map();
  view.drawn.forEach((d, id) => from.set(id, { x: d.x, y: d.y }));

  const step = (now) => {
    const t = duration ? Math.min(1, (now - start) / duration) : 1;
    const k = ease(t);

    view.drawn.forEach((d, id) => {
      const a = from.get(id);
      d.x = a.x + (d.to.x - a.x) * k;
      d.y = a.y + (d.to.y - a.y) * k;
      d.g.setAttribute('transform', `translate(${d.x.toFixed(1)} ${d.y.toFixed(1)})`);
      d.g.style.opacity = d.fading ? String(1 - k) : String(Math.max(k, t));
    });
    paintEdges();

    if (t < 1) {
      view.frame = requestAnimationFrame(step);
    } else {
      view.frame = null;
      view.drawn.forEach((d, id) => {
        if (!d.fading) return;
        d.g.remove();
        view.drawn.delete(id);
      });
      paintEdges();
    }
  };
  view.frame = requestAnimationFrame(step);
}

function paintEdges() {
  const lines = [];
  view.drawn.forEach((d, id) => {
    if (d.fading) return;
    (view.kids.get(id) || []).forEach((childId) => {
      const c = view.drawn.get(childId);
      if (!c || c.fading) return;
      const y1 = d.y + R, y2 = c.y - R, mid = (y1 + y2) / 2;
      lines.push(`M ${d.x.toFixed(1)} ${y1.toFixed(1)}
                  C ${d.x.toFixed(1)} ${mid.toFixed(1)},
                    ${c.x.toFixed(1)} ${mid.toFixed(1)},
                    ${c.x.toFixed(1)} ${y2.toFixed(1)}`);
    });
  });
  view.edges.innerHTML = lines.map((d) => `<path d="${d}" />`).join('');
}

/* ---------------------------------------------------------------- a node */

function nodeElement(node) {
  const g = document.createElementNS(SVG_NS, 'g');
  g.setAttribute('class', 'node');
  g.setAttribute('tabindex', '0');
  g.innerHTML = nodeMarkup(node);

  /*
    Clicking a cell goes to that cell -- that is what a cell on a map is for,
    and it is what people reach for first. Opening the branch is a separate,
    explicit control beside it, the way a file tree works.
  */
  g.addEventListener('click', (ev) => {
    if (ev.target.closest('.knob')) {
      ev.stopPropagation();
      return toggle(node.id);
    }
    if (node.id !== view.rootId) onOpen(node.id);
  });
  g.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') { ev.preventDefault(); if (node.id !== view.rootId) onOpen(node.id); }
    if (ev.key === ' ') { ev.preventDefault(); toggle(node.id); }
  });
  return g;
}

function refresh(g, node) {
  const open = view.expanded.has(node.id);
  g.setAttribute('class', 'node'
    + (node.id === view.rootId ? ' here' : '')
    + (node.child_count ? ' openable' : '')
    + (open ? ' open' : ''));
  g.innerHTML = nodeMarkup(node);
}

function nodeMarkup(node) {
  const c = 2 * Math.PI * R;
  const filled = (Math.max(0, Math.min(100, node.percent)) / 100) * c;
  const label = node.goal.length > 22 ? node.goal.slice(0, 20).trimEnd() + '…' : node.goal;
  const open = view.expanded.has(node.id);
  const inside = node.child_count && !open ? ` · ${node.child_count} inside` : '';

  /*
    A transparent rectangle over the whole node, drawn first so it sits
    underneath everything: SVG text has an unreliable hit box, so the target
    is the area a person aims at rather than the glyphs themselves.
  */
  return `<title>${esc(tooltip(node))}</title>
    <rect class="hit" x="${-GAP / 2 + 6}" y="${-R - 6}"
          width="${GAP - 12}" height="${R * 2 + 44}" />
    <circle class="dish" r="${R}" />
    <circle class="fill" r="${R}"
            stroke-dasharray="${filled.toFixed(1)} ${c.toFixed(1)}"
            transform="rotate(-90)" />
    ${node.attention
      ? `<circle class="flag ${esc((node.health || '').replace(' ', '-'))}"
                cx="${R - 3}" cy="${-R + 3}" r="3.5" />` : ''}
    <text class="pc" y="4">${node.percent}</text>
    ${node.child_count ? `<g class="knob">
        <circle class="knob-hit" cx="${R + 11}" cy="0" r="9" />
        <text class="knob-mark" x="${R + 11}" y="4">${open ? '−' : '+'}</text>
      </g>` : ''}
    <text class="name" y="${R + 17}">${esc(label)}</text>
    <text class="sub" y="${R + 31}">${
      plural(node.people, 'person', 'people')}${inside}</text>`;
}

function tooltip(n) {
  const bits = [n.goal, `${n.percent}% · ${plural(n.people, 'person', 'people')}`];
  if (n.remaining) bits.push(`${plural(n.remaining, 'thing')} left`);
  if (n.questions) bits.push(plural(n.questions, 'open question'));
  if (n.unowned) bits.push(`${plural(n.unowned, 'thing')} nobody has taken`);
  if (n.stalled) bits.push(`${plural(n.stalled, 'thing')} taken but not started`);
  if (n.health) bits.push('health: ' + n.health);
  (n.attention_says || []).forEach((a) => bits.push(a));
  if (n.because) {
    bits.push(`grew out of: ${n.because.work}`);
    if (n.because.question) bits.push(`asked as: ${n.because.question}`);
  }
  if (n.child_count) bits.push(`${plural(n.child_count, 'cell')} inside — use + to open`);
  return bits.join('\n');
}

/* ------------------------------------------------------------- expanding */

async function toggle(id) {
  const node = view.nodes.get(id);
  if (!node || !node.child_count) return;

  if (view.expanded.has(id)) {
    view.expanded.delete(id);
    collapseBelow(id);
    draw();
    return;
  }

  if (!view.kids.has(id)) {
    const g = view.drawn.get(id);
    if (g) g.g.classList.add('loading');
    try {
      const { children } = await api.childrenOf(id);
      children.forEach((c) => view.nodes.set(c.id, c));
      view.kids.set(id, children.map((c) => c.id));
    } catch (e) {
      if (g) g.g.classList.remove('loading');
      return;
    }
    if (g) g.g.classList.remove('loading');
  }
  view.expanded.add(id);
  draw();
  follow(id);
}

/* Closing a branch closes everything under it, so reopening starts clean. */
function collapseBelow(id) {
  (view.kids.get(id) || []).forEach((child) => {
    if (view.expanded.has(child)) { view.expanded.delete(child); collapseBelow(child); }
  });
}

/*
  Keep what you just opened in view. The map only ever scrolls sideways, so
  this is one smooth pan rather than a camera.
*/
function follow(id) {
  const mount = view.mount;
  const target = view.drawn.get(id);
  if (!mount || !target) return;

  requestAnimationFrame(() => {
    const scale = mount.clientWidth / (view.svg.viewBox.baseVal.width || 1);
    const centre = target.to.x * Math.min(1, scale);
    const wanted = Math.max(0, centre - mount.clientWidth / 2);
    if (Math.abs(wanted - mount.scrollLeft) < 24) return;
    mount.scrollTo({ left: wanted, behavior: 'smooth' });
  });
}

/* ---------------------------------------------------- the section wrapper */

/* The page renders a mount point; the map itself is attached to it after. */
export function mapMount() {
  return '<div class="map-scroll" data-map></div>';
}

export function mapCaption(root) {
  const said = [];
  if (root.questions) said.push(`${plural(root.questions, 'question')} still open`);
  if (root.unowned) said.push(`${plural(root.unowned, 'thing')} nobody has taken`);
  if (root.stalled) said.push(`${plural(root.stalled, 'thing')} taken but not started`);
  const hint = root.child_count
    ? '<span class="xs faint">click a cell to go there · + to open what is inside</span>' : '';
  if (!said.length) {
    return `<p class="xs faint">Nothing stuck anywhere below. ${hint}</p>`;
  }
  return `<p class="xs"><span style="color:var(--warn)">${esc(said.join(' · '))}</span>
    ${hint ? ' · ' + hint : ''}</p>`;
}
