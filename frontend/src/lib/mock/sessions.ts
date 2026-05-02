import type { ChatSession } from '@/lib/types';

export const sessions: ChatSession[] = [
  {
    id: 's1',
    title: 'Production deploy debrief',
    meetingId: 'm_demo',
    scope: 'meeting',
    isActive: true,
    relTime: '2 minutes ago',
    messages: [
      { role: 'user', text: 'what did mike commit to?' },
      {
        role: 'asst',
        text: "Mike took ownership of two action items from this meeting:\n\n1. Investigate the migration script — specifically whether the schema diff was ever tested against the old gateway path. [02:47]\n\n2. Pull CI history to confirm whether the payment-flow regression suite actually ran on this deploy, or whether the case was skipped. [03:42]\n\nHe's also the implicit owner on the rollback decision itself — that was his proposal that Anna and Sarah confirmed. [02:31]",
        model: 'claude-haiku-4.5',
        sources: 3,
        latency: '1.2s',
      },
      { role: 'user', text: 'and the regression suite — is that blocked on something specific?' },
      {
        role: 'asst',
        text: "Yes. Anna explicitly tagged the regression-suite question as needs-resolution before any redeploy attempt. [03:55] So Mike's CI-history pull is the unblocker — once that's clear, the team can decide whether to add a missing test case or fix a skipped one before retrying the eu-west-1 rollout.",
        model: 'claude-haiku-4.5',
        sources: 2,
        latency: '0.9s',
      },
      { role: 'user', text: 'what was the customer impact window?' },
      {
        role: 'asst',
        text: "About two minutes of degraded checkout in eu-west-1, between the canary alarms firing at 04:14 UTC and the rollback decision. [01:09] The state was fully restored by 05:01 UTC with card-auth latency back under p95 250ms. [05:36] Blast radius was contained — us-east-1 and ap-southeast hadn't been fanned out to yet. [06:02]",
        model: 'claude-haiku-4.5',
        sources: 3,
        latency: '1.4s',
      },
    ],
  },
  {
    id: 's2',
    title: 'Production deploy debrief',
    meetingId: 'm_demo',
    scope: 'meeting',
    isActive: false,
    relTime: '8 minutes ago',
    messages: [
      { role: 'user', text: "what's still unanswered?" },
      {
        role: 'asst',
        text: "One open question is currently unanswered:\n\n— Does the payment-flow regression suite have the missing case, or did the case exist and not run? [03:12]\n\nThis is gating any redeploy attempt, per Anna. The owner-less canary-monitoring decision is captured but doesn't have an owner assigned yet — Sarah said she'd draft a proposal but didn't commit to ownership without product input. [04:52]",
        model: 'claude-haiku-4.5',
        sources: 2,
        latency: '0.8s',
      },
      { role: 'user', text: 'thanks' },
    ],
  },
  {
    id: 's3',
    title: 'All meetings',
    meetingId: null,
    scope: 'all',
    isActive: false,
    relTime: '1 hour ago',
    messages: [
      { role: 'user', text: 'when did we last discuss the auth refactor?' },
      {
        role: 'asst',
        text: "Most recently in the auth refactor design review on Apr 17, 2026 — Lin walked the team through the gateway routing for the new auth path. The decision recorded there was that auth refactor work would route through the new gateway directly rather than the migration shim. [Apr 17 · 12:14]\n\nIt also came up briefly in this morning's production deploy debrief — Sarah asked whether the auth refactor was gated on the failed eu-west-1 rollout, and the team confirmed it isn't (different code path). [07:01]",
        model: 'claude-haiku-4.5',
        sources: 2,
        latency: '1.6s',
      },
      { role: 'user', text: 'who has been driving that work?' },
      {
        role: 'asst',
        text: 'Lin Chao has been the primary driver — she presented the design and owns most of the open action items from the Apr 17 review. Jordan Reyes and Sarah Chen are also participants on that thread. There are 3 open questions on the auth refactor across two meetings, all currently unanswered.',
        model: 'claude-haiku-4.5',
        sources: 3,
        latency: '1.3s',
      },
    ],
  },
];
