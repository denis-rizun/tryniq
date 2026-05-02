import type {
  ActionItem,
  Decision,
  Meeting,
  OpenQuestion,
  PreviousMeeting,
  Topic,
} from '@/lib/types';
import { utterances } from './utterances';

const decisions: Decision[] = [
  {
    id: 'd1',
    text: 'Roll back the eu-west-1 deploy and investigate the migration script after.',
    time: '02:31',
    owner: 'mike',
    status: 'confirmed',
  },
  {
    id: 'd2',
    text: 'Improve canary monitoring — tiered alert, recommend, auto-rollback.',
    time: '04:18',
    owner: null,
    status: 'confirmed',
  },
];

const actionItems: ActionItem[] = [
  {
    id: 'a1',
    text: 'Investigate the migration script — was the schema diff tested against the old gateway path?',
    time: '02:47',
    owner: 'mike',
    status: 'open',
  },
  {
    id: 'a2',
    text: 'Pull CI history to confirm whether the payment-flow regression suite ran on this deploy.',
    time: '03:42',
    owner: 'mike',
    status: 'open',
  },
  {
    id: 'a3',
    text: 'Draft a customer-facing postmortem by EOD Thursday.',
    time: '08:20',
    owner: 'sarah',
    status: 'open',
  },
  {
    id: 'a4',
    text: 'Improve canary monitoring — write proposal for tiered rollback signal.',
    time: '06:12',
    owner: null,
    status: 'open',
  },
];

const questions: OpenQuestion[] = [
  {
    id: 'q1',
    text: 'Does the payment-flow regression suite have the missing case, or did the case exist and not run?',
    time: '03:12',
    status: 'unanswered',
    stale: true,
  },
  {
    id: 'q2',
    text: 'Should we adjust canary thresholds or rely entirely on tiered automation?',
    time: '04:38',
    status: 'partially-answered',
  },
];

const topics: Topic[] = [
  {
    id: 't1',
    name: 'eu-west-1 rollout',
    summary: 'The rolling deploy that failed at 04:12 UTC, returning 502s on payment-flow traffic.',
  },
  {
    id: 't2',
    name: 'payment flow',
    summary:
      'Card auth path running through the migration shim — the surface where regression hit.',
    relatesPrevious: true,
  },
  {
    id: 't3',
    name: 'canary monitoring',
    summary: 'Whether existing alert thresholds are sufficient or need tiered automation.',
  },
  {
    id: 't4',
    name: 'migration shim',
    summary: 'Old schema, new query path. Suspected source of the gateway timeouts.',
  },
];

export const previousMeeting: PreviousMeeting = {
  id: 'm_pm_001',
  title: 'Payment flow architecture review',
  date: 'Apr 24, 2026',
  relatedTopics: ['payment flow', 'migration shim'],
};

export const meeting: Meeting = {
  id: 'm_demo',
  title: 'Production deploy debrief',
  startedAt: 'May 11, 2026 · 04:30 UTC',
  duration: '18:42',
  durationLive: '14:23',
  participants: ['sarah', 'mike', 'anna'],
  state: 'live',
  asrModel: 'whisper-large-v3',
  llmModel: 'claude-haiku-4.5',
  utterances,
  decisions,
  actionItems,
  questions,
  topics,
  speakingTime: { sarah: 38, mike: 35, anna: 27 },
  previousMeeting,
  summary:
    'Production deploy to eu-west-1 returned 502s on roughly 30% of card-auth traffic at 04:12 UTC. After two minutes of degraded checkout the team rolled back to last-known-good; eu-west-1 has been confirmed stable since 05:01 UTC. The blast radius was contained because us-east-1 and ap-southeast had not yet been fanned out to.\n\nDiscussion focused on whether faster rollback should be automated and whether the payment-flow regression suite has the right coverage. Mike owns the migration-script investigation and the CI-history pull; Sarah will draft the customer postmortem. One owner-less decision was captured around improving canary monitoring.',
};
