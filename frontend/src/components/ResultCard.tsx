import { AlertTriangle, BarChart3, Code2, Database, Table2, Wand2 } from "lucide-react";
import { useState } from "react";
import { humanize } from "../format";
import type { Theme } from "../theme";
import type { ChartType, ResultBlock } from "../types";
import { ChartView } from "./ChartView";
import { CodeBlock } from "./CodeBlock";
import { DataTable } from "./DataTable";
import { Markdown } from "./Markdown";
import { StatTile } from "./StatTile";

type Tab = "chart" | "table" | "code";

const CHART_LABELS: Record<ChartType, string> = { bar: "Bar", line: "Line", area: "Area", pie: "Donut", scatter: "Scatter" };

interface Props {
  block: ResultBlock;
  theme: Theme;
  showNarrative: boolean;
  question?: string;
}

export function ResultCard({ block, theme, showNarrative, question }: Props) {
  const hasChart = !!block.chart;
  const hasTable = !!block.table && block.table.rows.length > 0;
  const [tab, setTab] = useState<Tab>(hasChart ? "chart" : hasTable ? "table" : "code");
  const [chartType, setChartType] = useState<ChartType | null>(null);

  if (block.kind === "error") {
    return (
      <div className="result result--error">
        {showNarrative && block.narrative && <Markdown>{block.narrative}</Markdown>}
        {block.code && (
          <details className="result__details">
            <summary>Show the last code attempt</summary>
            <CodeBlock code={block.code} note={`${block.attempts} attempts`} />
          </details>
        )}
      </div>
    );
  }

  const tabs: { id: Tab; label: string; icon: JSX.Element; show: boolean }[] = [
    { id: "chart", label: "Chart", icon: <BarChart3 size={14} />, show: hasChart },
    { id: "table", label: "Table", icon: <Table2 size={14} />, show: hasTable },
    { id: "code", label: "Code", icon: <Code2 size={14} />, show: !!block.code },
  ];
  const visibleTabs = tabs.filter((t) => t.show);
  const activeType = chartType ?? block.chart?.type ?? "bar";

  return (
    <div className="result">
      {showNarrative && block.narrative && <Markdown>{block.narrative}</Markdown>}

      {block.kind === "scalar" && block.scalar && <StatTile label={block.scalar.label} value={block.scalar.value} />}
      {block.kind === "empty" && <div className="result__empty">No rows matched this question.</div>}

      {visibleTabs.length === 1 && visibleTabs[0].id === "code" && block.code && (
        <details className="result__details">
          <summary>Show the code behind this number</summary>
          <div className="panel"><CodeBlock code={block.code} /></div>
        </details>
      )}

      {(visibleTabs.length > 1 || (visibleTabs.length === 1 && visibleTabs[0].id !== "code")) && (
        <div className="panel">
          <div className="panel__head">
            <div className="tabs" role="tablist">
              {visibleTabs.map((t) => (
                <button key={t.id} role="tab" aria-selected={tab === t.id} className="tab" onClick={() => setTab(t.id)}>
                  {t.icon}
                  {t.label}
                </button>
              ))}
            </div>
            {tab === "chart" && block.chart && block.chart.alternatives.length > 1 && (
              <div className="seg seg--sm" aria-label="Chart type">
                {block.chart.alternatives.map((t) => (
                  <button key={t} aria-pressed={activeType === t} onClick={() => setChartType(t)}>
                    {CHART_LABELS[t]}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="panel__body">
            {tab === "chart" && block.chart && <ChartView spec={block.chart} type={activeType} theme={theme} />}
            {tab === "table" && block.table && <DataTable table={block.table} name={question ?? block.source} />}
            {tab === "code" && block.code && (
              <CodeBlock code={block.code} note={block.attempts > 1 ? `self-corrected in ${block.attempts} attempts` : undefined} />
            )}
          </div>
        </div>
      )}

      {(block.citation || block.warnings.length > 0) && (
        <div className="citation">
          {block.citation && (
            <span>
              <Database size={12} /> Computed from {block.citation.rows_scanned.toLocaleString()} rows of{" "}
              <b>{block.citation.sources.join(" + ")}</b>
              {block.citation.columns_used.length > 0 && (
                <>
                  {" "}using{" "}
                  {block.citation.columns_used.map((c) => (
                    <code key={c} className="citation__col">{humanize(c)}</code>
                  ))}
                </>
              )}
            </span>
          )}
          {block.warnings.map((w) => (
            <span key={w} className="citation__warn">
              {w.startsWith("Self-corrected") ? <Wand2 size={12} /> : <AlertTriangle size={12} />} {w}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
