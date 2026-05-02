import type { Meeting } from '@/lib/types';

export type BlockState = Record<string, boolean>;

export const buildPreview = (meeting: Meeting, blocks: BlockState): string => {
  const lines: string[] = [];
  lines.push(`# ${meeting.title}`);
  lines.push(`_${meeting.startedAt} · ${meeting.duration || meeting.durationLive}_\n`);
  if (blocks.summary) lines.push(`## Summary\n${meeting.summary}\n`);
  if (blocks.decisions) {
    lines.push('## Decisions');
    for (const d of meeting.decisions) lines.push(`- ${d.text} _(→ ${d.time})_`);
    lines.push('');
  }
  if (blocks.actions) {
    lines.push('## Action items');
    for (const a of meeting.actionItems) {
      lines.push(`- ${a.text} _(→ ${a.time}, owner: ${a.owner || 'unassigned'})_`);
    }
    lines.push('');
  }
  if (blocks.questions) {
    lines.push('## Open questions');
    for (const q of meeting.questions) lines.push(`- ${q.text} _(→ ${q.time}, ${q.status})_`);
    lines.push('');
  }
  if (blocks.transcript) {
    lines.push('## Transcript');
    for (const u of meeting.utterances.slice(0, 12)) {
      lines.push(`**${u.speaker}** [${u.time}] ${u.text}\n`);
    }
    lines.push(`_…${meeting.utterances.length - 12} more utterances_\n`);
  }
  if (blocks.speakers) {
    lines.push('## Speakers');
    for (const pid of meeting.participants) lines.push(`- ${pid}: ${meeting.speakingTime[pid]}%`);
  }
  return lines.join('\n');
};
