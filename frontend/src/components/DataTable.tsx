import { ArrowDown, ArrowUp, Download } from "lucide-react";
import { useMemo, useState } from "react";
import { download, formatCell, humanize, slug, toCsv } from "../format";
import type { TableData } from "../types";

interface Props {
  table: TableData;
  name?: string;
  maxHeight?: number;
  humanizeHeaders?: boolean;
}

export function DataTable({ table, name = "result", maxHeight = 360, humanizeHeaders = true }: Props) {
  const [sort, setSort] = useState<{ col: number; dir: 1 | -1 } | null>(null);

  const numericCols = useMemo(
    () => table.columns.map((_, i) => table.rows.length > 0 && table.rows.every((r) => r[i] === null || typeof r[i] === "number")),
    [table],
  );

  const rows = useMemo(() => {
    if (!sort) return table.rows;
    const { col, dir } = sort;
    return [...table.rows].sort((a, b) => {
      const x = a[col], y = b[col];
      if (x === y) return 0;
      if (x === null || x === undefined) return 1;
      if (y === null || y === undefined) return -1;
      return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true })) * dir;
    });
  }, [table.rows, sort]);

  const onSort = (col: number) =>
    setSort((s) => (s?.col !== col ? { col, dir: numericCols[col] ? -1 : 1 } : s.dir === 1 ? { col, dir: -1 } : { col, dir: 1 }));

  return (
    <div className="table-wrap">
      <div className="table-scroll" style={{ maxHeight }}>
        <table className="data-table">
          <thead>
            <tr>
              {table.columns.map((c, i) => (
                <th key={c + i} className={numericCols[i] ? "num" : undefined}>
                  <button type="button" onClick={() => onSort(i)} title={`Sort by ${c}`}>
                    {humanizeHeaders ? humanize(c) : c}
                    {sort?.col === i && (sort.dir === 1 ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, ri) => (
              <tr key={ri}>
                {r.map((v, ci) => (
                  <td key={ci} className={numericCols[ci] ? "num" : undefined}>{formatCell(v)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-foot">
        <span>
          {table.rows.length.toLocaleString()} {table.rows.length === 1 ? "row" : "rows"}
          {table.total_rows > table.rows.length && ` of ${table.total_rows.toLocaleString()}`}
        </span>
        <button type="button" className="btn btn--ghost btn--xs" onClick={() => download(`${slug(name)}.csv`, toCsv(table.columns, rows))}>
          <Download size={13} /> CSV
        </button>
      </div>
    </div>
  );
}
