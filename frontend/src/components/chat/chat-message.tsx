import { memo, useMemo } from 'react';
import type { ChatCitationView, ChatMessage as ChatMessageType } from '@/lib/types';

const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const buildCitationRegex = (labels: string[]): RegExp | null => {
  if (labels.length === 0) return null;
  const sorted = [...new Set(labels)].sort((a, b) => b.length - a.length).map(escapeRegex);
  return new RegExp(`(\\[(?:${sorted.join('|')})\\])`, 'g');
};

const renderAsstText = (
  text: string,
  re: RegExp | null,
  labelMap: Map<string, ChatCitationView>,
  onCite?: (c: ChatCitationView) => void,
) => {
  if (!re) {
    return [
      <span key={0} style={{ whiteSpace: 'pre-wrap' }}>
        {text}
      </span>,
    ];
  }
  return text.split(re).map((part, i) => {
    const inner = /^\[(.+)\]$/.exec(part);
    if (inner) {
      const c = labelMap.get(inner[1]);
      if (c) {
        return (
          <span
            key={i}
            className="cite-chip mono"
            onClick={() => onCite?.(c)}
            style={{ marginLeft: 0 }}
          >
            {c.label}
          </span>
        );
      }
    }
    return (
      <span key={i} style={{ whiteSpace: 'pre-wrap' }}>
        {part}
      </span>
    );
  });
};

interface ChatMessageProps {
  m: ChatMessageType;
  onCite?: (c: ChatCitationView) => void;
  animate?: boolean;
}

const ChatMessageImpl = ({ m, onCite, animate }: ChatMessageProps) => {
  const citations = m.citations;
  const re = useMemo(
    () => buildCitationRegex((citations ?? []).map((c) => c.label)),
    [citations],
  );
  const labelMap = useMemo(
    () => new Map((citations ?? []).map((c) => [c.label, c] as const)),
    [citations],
  );

  if (m.role === 'user') return <div className="chat-msg-user">{m.text}</div>;

  // Word-by-word animation only on settled messages — animating during token stream
  // remounts every span on every token (O(N²) and visually glitchy).
  const showWordAnim = animate && !m.pending;
  const words = showWordAnim ? m.text.split(/(\s+)/) : null;

  return (
    <div>
      <div className="chat-msg-asst">
        {words
          ? words.map((w, i) =>
              /^\s+$/.test(w) ? (
                <span key={i}>{w}</span>
              ) : (
                <span key={i} className="word-in" style={{ animationDelay: `${i * 30}ms` }}>
                  {renderAsstText(w, re, labelMap, onCite)}
                </span>
              ),
            )
          : renderAsstText(m.text, re, labelMap, onCite)}
      </div>
      {m.model && (
        <div className="chat-msg-asst-meta mono">
          {m.model}
          {m.sources ? ` · ${m.sources} sources` : ''}
          {m.latency ? ` · ${m.latency}` : ''}
        </div>
      )}
    </div>
  );
};

export const ChatMessage = memo(ChatMessageImpl);
