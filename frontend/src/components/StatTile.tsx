import { formatCell, formatNumber, humanize } from "../format";

export function StatTile({ label, value }: { label: string; value: unknown }) {
  const isNum = typeof value === "number";
  const pct = /pct|percent|rate|share/i.test(label);
  return (
    <div className="stat">
      <div className="stat__label">{humanize(label)}</div>
      <div className="stat__value" title={isNum ? formatNumber(value) : undefined}>
        {isNum ? formatNumber(value, "compact") : formatCell(value)}
        {isNum && pct && <span className="stat__unit">%</span>}
      </div>
      {isNum && Math.abs(value) >= 10_000 && <div className="stat__exact">{formatNumber(value)}</div>}
    </div>
  );
}
