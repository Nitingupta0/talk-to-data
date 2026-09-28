import { AlertCircle, HelpCircle, Sparkles } from "lucide-react";
import { useState } from "react";
import type { Theme } from "../theme";
import type { Message } from "../types";
import { Markdown } from "./Markdown";
import { ResultCard } from "./ResultCard";

interface Props {
  message: Message;
  theme: Theme;
  onAsk: (q: string) => void;
  isLatest: boolean;
  busy: boolean;
}

export function MessageView({ message, theme, onAsk, isLatest, busy }: Props) {
  if (message.role === "user") {
    return (
      <div className="msg msg--user">
        <div className="bubble">{message.content}</div>
      </div>
    );
  }
  return <AssistantMessage message={message} theme={theme} onAsk={onAsk} isLatest={isLatest} busy={busy} />;
}

function AssistantMessage({ message, theme, onAsk, isLatest, busy }: Props) {
  const results = message.results ?? [];
  const multi = results.length > 1;
  const [active, setActive] = useState(0);
  const kind = message.kind ?? "respond";

  const icon =
    kind === "error" ? <AlertCircle size={16} /> : kind === "clarify" ? <HelpCircle size={16} /> : <Sparkles size={16} />;

  return (
    <div className={`msg msg--assistant msg--${kind}`}>
      <div className="avatar" aria-hidden>{icon}</div>
      <div className="msg__body">
        {(multi || results.length === 0) && <Markdown>{message.content}</Markdown>}

        {multi && (
          <div className="file-tabs" role="tablist">
            {results.map((r, i) => (
              <button key={i} role="tab" aria-selected={active === i} className="file-tab" onClick={() => setActive(i)}>
                <span className={`file-tab__dot ${r.kind === "error" ? "is-error" : ""}`} />
                {r.source}
              </button>
            ))}
          </div>
        )}
        {results.map((r, i) =>
          !multi || i === active ? (
            <ResultCard key={i} block={r} theme={theme} showNarrative question={message.question} />
          ) : null,
        )}

        {message.follow_ups && message.follow_ups.length > 0 && (isLatest || kind === "welcome") && (
          <div className="suggestions">
            {kind !== "welcome" && <span className="suggestions__label">Ask next</span>}
            {message.follow_ups.map((q) => (
              <button key={q} className="chip" disabled={busy} onClick={() => onAsk(q)}>
                {q}
              </button>
            ))}
          </div>
        )}

        {message.duration_ms !== undefined && kind === "answer" && (
          <div className="msg__meta">
            {message.intent && <span className="tag">{message.intent}</span>}
            {message.mode === "merge" && <span className="tag">merged files</span>}
            <span>{(message.duration_ms / 1000).toFixed(1)}s</span>
          </div>
        )}
      </div>
    </div>
  );
}
