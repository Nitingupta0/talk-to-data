import { ArrowUp, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ChatMode } from "../types";

interface Props {
  disabled: boolean;
  busy: boolean;
  placeholder: string;
  multiFile: boolean;
  mode: ChatMode;
  onMode: (m: ChatMode) => void;
  onSend: (text: string) => void;
  onStop: () => void;
}

const MODES: { id: ChatMode; label: string; hint: string }[] = [
  { id: "auto", label: "Auto", hint: "Per file, unless you say “combine”" },
  { id: "separate", label: "Per file", hint: "Answer for each file separately" },
  { id: "merge", label: "Merge", hint: "Stack all files into one table (adds a source_file column)" },
];

export function Composer({ disabled, busy, placeholder, multiFile, mode, onMode, onSend, onStop }: Props) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [text]);

  useEffect(() => {
    if (!busy) ref.current?.focus();
  }, [busy]);

  const submit = () => {
    const t = text.trim();
    if (!t || disabled || busy) return;
    onSend(t);
    setText("");
  };

  return (
    <div className="composer-wrap">
      {multiFile && (
        <div className="composer__modes">
          <span>Multiple files:</span>
          <div className="seg seg--sm">
            {MODES.map((m) => (
              <button key={m.id} aria-pressed={mode === m.id} title={m.hint} onClick={() => onMode(m.id)}>
                {m.label}
              </button>
            ))}
          </div>
        </div>
      )}
      <form className={`composer ${disabled ? "is-disabled" : ""}`} onSubmit={(e) => { e.preventDefault(); submit(); }}>
        <textarea
          ref={ref}
          rows={1}
          value={text}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          maxLength={2000}
          aria-label="Ask a question about your data"
        />
        {busy ? (
          <button type="button" className="send-btn" onClick={onStop} aria-label="Stop">
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button type="submit" className="send-btn" disabled={!text.trim() || disabled} aria-label="Send">
            <ArrowUp size={18} />
          </button>
        )}
      </form>
      <div className="composer__hint">
        The model only sees your column names and a few sample values — every number comes from code run on your data.
      </div>
    </div>
  );
}
