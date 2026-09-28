import { Check, Loader2 } from "lucide-react";
import type { StatusEvent } from "../types";

const STEPS: { stage: StatusEvent["stage"][]; label: string }[] = [
  { stage: ["plan"], label: "Understand" },
  { stage: ["code", "repair"], label: "Write code" },
  { stage: ["run"], label: "Run" },
  { stage: ["explain"], label: "Explain" },
];

export function Progress({ status }: { status: StatusEvent | null }) {
  const current = status ? STEPS.findIndex((s) => s.stage.includes(status.stage)) : 0;
  return (
    <div className="progress" aria-live="polite">
      <ol className="progress__steps">
        {STEPS.map((s, i) => (
          <li key={s.label} className={i < current ? "done" : i === current ? "active" : ""}>
            <span className="progress__dot">
              {i < current ? <Check size={11} strokeWidth={3} /> : i === current ? <Loader2 size={11} className="spin" /> : null}
            </span>
            {s.label}
          </li>
        ))}
      </ol>
      <div className="progress__label">
        {status?.label ?? "Thinking"}
        {status?.source ? <span className="progress__source"> · {status.source}</span> : null}
        <span className="dots" />
      </div>
    </div>
  );
}
