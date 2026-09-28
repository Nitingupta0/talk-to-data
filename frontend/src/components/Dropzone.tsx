import { Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

const ACCEPT = ".csv,.tsv,.txt,.xlsx,.xlsm,.xls,.json,.parquet";

interface Props {
  onFiles: (files: File[]) => void;
  uploading: boolean;
  compact?: boolean;
}

export function Dropzone({ onFiles, uploading, compact }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      className={`dropzone ${over ? "is-over" : ""} ${compact ? "dropzone--compact" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const files = Array.from(e.dataTransfer.files);
        if (files.length) onFiles(files);
      }}
      onClick={() => !uploading && input.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
    >
      <input ref={input} type="file" multiple accept={ACCEPT} hidden
        onChange={(e) => { const f = Array.from(e.target.files ?? []); if (f.length) onFiles(f); e.target.value = ""; }} />
      {uploading ? <Loader2 className="spin" size={compact ? 18 : 28} /> : <UploadCloud size={compact ? 18 : 28} />}
      <div>
        <div className="dropzone__title">{uploading ? "Reading and profiling…" : compact ? "Upload files" : "Drop files here or click to browse"}</div>
        {!compact && <div className="dropzone__sub">CSV, TSV, Excel (every sheet), JSON or Parquet · up to 50 MB</div>}
      </div>
    </div>
  );
}
