import { Calendar, Hash, Key, Loader2, Tag, Type, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { formatCell } from "../format";
import type { ColumnProfile, DatasetDetail, Role } from "../types";
import { DataTable } from "./DataTable";

const ROLE_META: Record<Role, { label: string; icon: JSX.Element }> = {
  metric: { label: "Metric", icon: <Hash size={12} /> },
  dimension: { label: "Category", icon: <Tag size={12} /> },
  time: { label: "Time", icon: <Calendar size={12} /> },
  id: { label: "ID", icon: <Key size={12} /> },
  text: { label: "Text", icon: <Type size={12} /> },
};

export function Inspector({ datasetId, onClose }: { datasetId: string; onClose: () => void }) {
  const [ds, setDs] = useState<DatasetDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"columns" | "preview">("columns");

  useEffect(() => {
    setDs(null);
    setError(null);
    api.getDataset(datasetId, 100).then(setDs).catch((e) => setError(e.message));
  }, [datasetId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="scrim is-open scrim--drawer" onClick={onClose} />
      <aside className="drawer" aria-label="Dataset details">
        <div className="drawer__head">
          <div>
            <div className="drawer__eyebrow">Dataset</div>
            <h2>{ds?.name ?? "Loading…"}</h2>
            {ds && (
              <div className="drawer__meta">
                {ds.rows.toLocaleString()} rows · {ds.cols} columns · {ds.profile.memory_kb.toLocaleString()} KB
              </div>
            )}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        {error && <div className="alert alert--error">{error}</div>}
        {!ds && !error && <div className="drawer__loading"><Loader2 className="spin" /></div>}
        {ds && (
          <>
            {ds.insights?.summary && <p className="drawer__summary">{ds.insights.summary}</p>}
            <div className="seg drawer__tabs">
              <button aria-pressed={tab === "columns"} onClick={() => setTab("columns")}>Columns</button>
              <button aria-pressed={tab === "preview"} onClick={() => setTab("preview")}>Preview</button>
            </div>
            <div className="drawer__body">
              {tab === "columns" ? (
                <div className="col-list">
                  {ds.profile.columns.map((c) => <ColumnCard key={c.name} col={c} rows={ds.rows} />)}
                  {ds.semantics.rules.length > 0 && (
                    <div className="rules">
                      <div className="rules__title">Rules the assistant follows for this file</div>
                      <ul>{ds.semantics.rules.map((r) => <li key={r}>{r}</li>)}</ul>
                    </div>
                  )}
                </div>
              ) : (
                <DataTable table={ds.preview} name={ds.name} maxHeight={640} humanizeHeaders={false} />
              )}
            </div>
          </>
        )}
      </aside>
    </>
  );
}

function ColumnCard({ col, rows }: { col: ColumnProfile; rows: number }) {
  const meta = ROLE_META[col.role];
  const topMax = col.top_values?.[0]?.count ?? 1;
  return (
    <div className="col-card">
      <div className="col-card__head">
        <span className="col-card__name">{col.name}</span>
        <span className={`role role--${col.role}`}>{meta.icon}{meta.label}</span>
      </div>
      <div className="col-card__facts">
        <span>{col.unique.toLocaleString()} unique</span>
        {col.nulls > 0 ? <span className="warn">{col.null_pct}% empty</span> : <span>no blanks</span>}
        <span className="muted">{col.dtype}</span>
      </div>
      {col.stats && col.role === "metric" && (
        <div className="col-card__stats">
          {(["min", "50%", "mean", "max"] as const).map((k) => (
            <div key={k}><span>{k === "50%" ? "median" : k}</span><b>{formatCell(col.stats?.[k])}</b></div>
          ))}
        </div>
      )}
      {col.stats && col.role === "time" && col.stats.min !== undefined && (
        <div className="col-card__facts"><span>{formatCell(col.stats.min)} → {formatCell(col.stats.max)}</span></div>
      )}
      {col.top_values && col.top_values.length > 0 && (
        <div className="bars">
          {col.top_values.map((t) => (
            <div key={String(t.value)} className="bars__row" title={`${t.count} of ${rows}`}>
              <span className="bars__label">{formatCell(t.value)}</span>
              <span className="bars__track"><span className="bars__fill" style={{ width: `${(t.count / topMax) * 100}%` }} /></span>
              <span className="bars__count">{t.count.toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
