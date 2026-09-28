import { Code2, FileSpreadsheet, MessageSquareText, ShieldCheck, Sparkles } from "lucide-react";
import type { Dataset } from "../types";
import { Dropzone } from "./Dropzone";

interface Props {
  datasets: Dataset[];
  samples: { name: string; size_kb: number }[];
  uploading: boolean;
  onUpload: (files: File[]) => void;
  onSample: (name: string) => void;
  onAttach: (id: string) => void;
}

export function Onboarding({ datasets, samples, uploading, onUpload, onSample, onAttach }: Props) {
  return (
    <div className="onboarding">
      <div className="onboarding__hero">
        <div className="eyebrow"><Sparkles size={14} /> Plain-English analytics</div>
        <h1>Ask your data anything.</h1>
        <p>
          Upload a spreadsheet and ask questions the way you'd ask a colleague. You get an answer, a chart,
          the table behind it — and the exact code that produced every number.
        </p>
      </div>

      <Dropzone onFiles={onUpload} uploading={uploading} />

      {(samples.length > 0 || datasets.length > 0) && (
        <div className="onboarding__pick">
          {samples.length > 0 && (
            <div>
              <div className="onboarding__label">Try a sample</div>
              <div className="pick-list">
                {samples.map((s) => (
                  <button key={s.name} className="pick" onClick={() => onSample(s.name)} disabled={uploading}>
                    <FileSpreadsheet size={16} />
                    <span>{s.name}</span>
                    <small>{s.size_kb} KB</small>
                  </button>
                ))}
              </div>
            </div>
          )}
          {datasets.length > 0 && (
            <div>
              <div className="onboarding__label">Or reuse from your library</div>
              <div className="pick-list">
                {datasets.slice(0, 6).map((d) => (
                  <button key={d.id} className="pick" onClick={() => onAttach(d.id)}>
                    <FileSpreadsheet size={16} />
                    <span>{d.name}</span>
                    <small>{d.rows.toLocaleString()} rows</small>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <ol className="how">
        <li>
          <MessageSquareText size={18} />
          <div><b>You ask</b><span>The model sees only column names, types and a few sample values.</span></div>
        </li>
        <li>
          <Code2 size={18} />
          <div><b>It writes pandas</b><span>Code runs in a locked-down sandbox, and repairs itself if it fails.</span></div>
        </li>
        <li>
          <ShieldCheck size={18} />
          <div><b>Answers from results</b><span>The summary is written from the computed output, never from memory.</span></div>
        </li>
      </ol>
    </div>
  );
}
