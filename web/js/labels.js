/*
  Words.

  A state is a fact the server decided; how it reads in English is the
  interface's business, and this is the only place that translation happens.
  Adding a state here does not change what the system does -- if a state is
  missing, it shows as itself rather than as a lie.
*/

/*
  A question's stage, said as what is expected rather than what the object is
  called. Nobody should have to learn the word "leader_resolution" to know
  that somebody is waiting on somebody.
*/
const STAGES = {
  draft: ['not asked yet', ''],
  open: ['being talked through', 'live'],
  voting: ['everyone is answering', 'live'],
  leader_resolution: ['waiting on a decision', 'waiting'],
  accepted: ['settled', ''],
  executing: ['being done', ''],
  completed: ['done — worth recording', 'live'],
  knowledge: ['recorded', ''],
  rejected: ['declined', ''],
};

export const stage = (state) => (STAGES[state] || [state.replace(/_/g, ' '), ''])[0];
export const stageTone = (state) => (STAGES[state] || ['', ''])[1];

/* When it is this person the question is waiting for, say so instead. */
export function expectation(d) {
  if (d.state === 'voting' && !d.your_vote) return ['your answer', 'waiting'];
  return [stage(d.state), stageTone(d.state)];
}

export const ROLE_WORDS = {
  leader: 'accountable',
  responsible: 'doing it',
  verifier: 'checks it',
  participant: 'took part',
};

const HAPPENED = {
  UserRegistered: 'joined CellOS',
  CellCreated: 'created this cell',
  TaskExpanded: 'judged the work too large for one person',
  GoalRefined: 'changed the goal',
  RelationshipFormed: 'connected two things',
  DecisionCreated: 'raised a decision',
  DecisionOpened: 'opened it for discussion',
  RemarkAdded: 'said something',
  VotingOpened: 'called a vote',
  ResolutionRequested: 'asked for a decision',
  VoteSubmitted: 'voted',
  DecisionAccepted: 'accepted a decision',
  DecisionReturned: 'sent a decision back',
  DecisionRejected: 'declined a decision',
  LeaderOverride: 'decided against the vote',
  ExecutionStarted: 'started the work',
  ExecutionCompleted: 'finished the work',
  ExecutionResumed: 'reopened the work',
  KnowledgeRecorded: 'recorded how it turned out',
  TaskCreated: 'added work',
  TaskGenerated: 'turned a decision into work',
  TaskAssigned: 'took on work',
  ProgressUpdated: 'reported progress',
  TaskCompleted: 'finished something',
  TaskReopened: 'reopened something',
  EvidenceAttached: 'attached evidence',
};

export function happened(event) {
  const who = event.actor_name || 'someone';
  if (event.type === 'MemberJoined') {
    return event.actor_id === event.subject_id
      ? `${who} started this cell off`
      : `${who} brought in ${event.subject_name || 'someone'}`;
  }
  if (event.type === 'MemberRoleChanged') {
    return `${who} made ${event.subject_name || 'someone'} a ${event.payload.role}`;
  }
  return `${who} ${HAPPENED[event.type] || event.type}`;
}

export const GOVERNANCE = {
  informal: 'small enough to just decide',
  vote_decides: 'the cell votes and the count decides',
  leader_confirms_vote: 'the cell votes and a leader confirms it',
};

/*
  Health is a diagnosis, not a score. The words matter more than the number
  behind them, and the number is deliberately not shown.
*/
export const HEALTH_WORD = {
  excellent: 'Excellent',
  good: 'Good',
  moderate: 'Moderate',
  'at risk': 'At risk',
  critical: 'Critical',
};

export const MOMENTUM_WORD = {
  rising: '↑ improving',
  steady: '→ holding steady',
  falling: '↓ slipping',
  unknown: 'too early to say',
};
