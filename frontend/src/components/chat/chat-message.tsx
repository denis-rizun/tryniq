import { memo, useMemo } from 'react';
import { Streamdown } from 'streamdown';
import type { ChatCitationView, ChatMessage as ChatMessageType } from '@/lib/types';

const CITE_HREF_PREFIX = '#cite-';

const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const buildCitationRegex = (labels: string[]): RegExp | null => {
  if (labels.length === 0) return null;
  const sorted = [...new Set(labels)].sort((a, b) => b.length - a.length).map(escapeRegex);
  return new RegExp(`\\[(${sorted.join('|')})\\]`, 'g');
};

const annotateCitations = (text: string, re: RegExp | null): string => {
  if (!re) return text;
  return text.replace(
    re,
    (_, label) => `[${label}](${CITE_HREF_PREFIX}${encodeURIComponent(label)})`,
  );
};

interface ChatMessageProps {
  m: ChatMessageType;
  onCite?: (c: ChatCitationView) => void;
  animate?: boolean;
}

const ChatMessageImpl = ({ m, onCite }: ChatMessageProps) => {
  const citations = m.citations;
  const re = useMemo(() => buildCitationRegex((citations ?? []).map((c) => c.label)), [citations]);
  const labelMap = useMemo(
    () => new Map((citations ?? []).map((c) => [c.label, c] as const)),
    [citations],
  );
  const annotated = useMemo(() => annotateCitations(m.text, re), [m.text, re]);

  if (m.role === 'user') return <div className="chat-msg-user">{m.text}</div>;

  const components = {
    a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
      if (href?.startsWith(CITE_HREF_PREFIX)) {
        const label = decodeURIComponent(href.slice(CITE_HREF_PREFIX.length));
        const c = labelMap.get(label);
        if (c) {
          return (
            <span className="cite-chip mono" onClick={() => onCite?.(c)}>
              {c.label}
            </span>
          );
        }
      }
      return (
        <a href={href} target="_blank" rel="noreferrer">
          {children}
        </a>
      );
    },
  };

  return (
    <div>
      <div className="chat-msg-asst chat-md">
        <Streamdown components={components}>{annotated}</Streamdown>
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
