/* The only place that talks to the server. */

const TOKEN_KEY = 'cellos.token';

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request(method, path, body) {
  const auth = token.get();
  const res = await fetch(path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(auth ? { Authorization: 'Bearer ' + auth } : {}),
    },
    body: method === 'GET' ? undefined : JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({ error: 'The server said nothing.' }));
  if (!res.ok) throw new Error(data.error || 'Something went wrong.');
  return data;
}

export const api = {
  me: () => request('GET', '/api/me'),
  signIn: (name, email) => request('POST', '/api/session', { name, email }),
  signOut: () => request('DELETE', '/api/session', { token: token.get() }),

  home: () => request('GET', '/api/home'),
  cell: (id) => request('GET', '/api/cells/' + id),
  task: (id) => request('GET', '/api/tasks/' + id),
  yours: () => request('GET', '/api/yours'),
  noteOnTask: (id, body) => request('POST', `/api/tasks/${id}/notes`, { body }),
  /* One ring of the map, fetched when somebody opens a node. */
  childrenOf: (id) => request('GET', `/api/cells/${id}/children`),
  createCell: (goal, parent_id) => request('POST', '/api/cells', { goal, parent_id }),
  refineGoal: (id, goal) => request('PATCH', '/api/cells/' + id, { goal }),
  history: (id) => request('GET', `/api/cells/${id}/history`),

  admit: (id, person) => request('POST', `/api/cells/${id}/members`, person),
  propose: (id, decision) => request('POST', `/api/cells/${id}/decisions`, decision),
  addTask: (id, title) => request('POST', `/api/cells/${id}/tasks`, { title }),

  remark: (id, body, option) =>
    request('POST', `/api/decisions/${id}/remarks`, { body, option_id: option || null }),
  vote: (id, option_id) => request('POST', `/api/decisions/${id}/votes`, { option_id }),
  /* Every state change: the server named the step, the client fires it. */
  step: (id, step, args) => request('POST', `/api/decisions/${id}/steps/${step}`, args),

  updateTask: (id, patch) => request('PATCH', '/api/tasks/' + id, patch),
  splitOffTask: (id, goal) => request('POST', `/api/tasks/${id}/cell`, { goal }),
  /* What a cell holds itself to: a budget, a date, either or neither. */
  setCommitments: (id, body) => request('PUT', `/api/cells/${id}/commitments`, body),
  attachEvidence: (payload) => request('POST', '/api/evidence', payload),
};
