import { Check, Copy } from "lucide-react";
import { useState } from "react";

const KEYWORDS = /\b(import|from|as|def|return|if|elif|else|for|in|not|and|or|is|None|True|False|lambda|with)\b/g;

/** Minimal Python highlighter: strings, comments, numbers and keywords. */
function highlight(code: string): string {
  const esc = code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return esc
    .split("\n")
    .map((line) => {
      const parts: string[] = [];
      const re = /(#.*$)|('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")/g;
      let last = 0;
      let m: RegExpExecArray | null;
      const plain = (s: string) =>
        s.replace(KEYWORDS, '<span class="tok-k">$1</span>').replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="tok-n">$1</span>');
      while ((m = re.exec(line))) {
        parts.push(plain(line.slice(last, m.index)));
        parts.push(m[1] ? `<span class="tok-c">${m[1]}</span>` : `<span class="tok-s">${m[2]}</span>`);
        last = m.index + m[0].length;
      }
      parts.push(plain(line.slice(last)));
      return parts.join("");
    })
    .join("\n");
}

export function CodeBlock({ code, note }: { code: string; note?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked */
    }
  };
  return (
    <div className="code">
      <div className="code__bar">
        <span>pandas · executed in a sandbox{note ? ` · ${note}` : ""}</span>
        <button type="button" className="btn btn--ghost btn--xs" onClick={copy}>
          {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>
        <code dangerouslySetInnerHTML={{ __html: highlight(code) }} />
      </pre>
    </div>
  );
}
