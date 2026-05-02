import type { ChatMessage as ChatMessageType } from '@/lib/types';

const CITE_RE = /(\[\d{2}:\d{2}\]|\[[A-Z][a-z]{2} \d{1,2}[^\]]*\])/g;

const renderAsstText = (text: string, onCite?: (time: string) => void) =>
  text.split(CITE_RE).map((p, i) => {
    if (/^\[\d{2}:\d{2}\]$/.test(p) || /^\[[A-Z][a-z]{2}/.test(p)) {
      const t = p.slice(1, -1);
      return (
        <span
          key={i}
          className="cite-chip mono"
          onClick={() => onCite?.(t)}
          style={{ marginLeft: 0 }}
        >
          {t}
        </span>
      );
    }
    return (
      <span key={i} style={{ whiteSpace: 'pre-wrap' }}>
        {p}
      </span>
    );
  });

interface ChatMessageProps {
  m: ChatMessageType;
  onCite?: (time: string) => void;
  animate?: boolean;
}

export const ChatMessage = ({ m, onCite, animate }: ChatMessageProps) => {
  if (m.role === 'user') return <div className="chat-msg-user">{m.text}</div>;
  const words = m.text.split(/(\s+)/);
  return (
    <div>
      <div className="chat-msg-asst">
        {animate
          ? words.map((w, i) =>
              /^\s+$/.test(w) ? (
                <span key={i}>{w}</span>
              ) : (
                <span key={i} className="word-in" style={{ animationDelay: `${i * 30}ms` }}>
                  {renderAsstText(w, onCite)}
                </span>
              ),
            )
          : renderAsstText(m.text, onCite)}
      </div>
      {m.model && (
        <div className="chat-msg-asst-meta mono">
          {m.model} · {m.sources} sources · {m.latency}
        </div>
      )}
    </div>
  );
};
