import { useMemo } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { formatCell, humanize } from "../format";
import { CHART_INK, SERIES, type Theme } from "../theme";
import type { ChartSpec, ChartType } from "../types";

interface Props {
  spec: ChartSpec;
  type: ChartType;
  theme: Theme;
}

interface TipProps {
  active?: boolean;
  label?: unknown;
  payload?: { name?: string; value?: unknown; color?: string; payload?: Record<string, unknown> }[];
  xKey: string;
  pie?: boolean;
}

function ChartTooltip({ active, payload, label, xKey, pie }: TipProps) {
  if (!active || !payload?.length) return null;
  const title = pie ? payload[0].payload?.[xKey] : label;
  return (
    <div className="chart-tip">
      <div className="chart-tip__title">{formatCell(title)}</div>
      {payload.map((p, i) => (
        <div className="chart-tip__row" key={i}>
          <span className="chart-tip__swatch" style={{ background: p.color ?? (p.payload?.fill as string) }} />
          <span className="chart-tip__name">{humanize(String(p.name ?? ""))}</span>
          <span className="chart-tip__value">{formatCell(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

const compactTick = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 });
const tick = (v: unknown) => (typeof v === "number" ? compactTick.format(v) : truncate(String(v), 14));
const truncate = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

export function ChartView({ spec, type, theme }: Props) {
  const colors = SERIES[theme];
  const ink = CHART_INK[theme];
  const { data, x, series } = spec;
  const multi = series.length > 1;

  const longLabels = useMemo(
    () => data.some((d) => String(d[x] ?? "").length > 10) || data.length > 10,
    [data, x],
  );
  const horizontal = type === "bar" && !spec.time_x && longLabels;
  const height = horizontal ? Math.min(Math.max(data.length * 34 + 60, 240), 720) : 320;

  const axisProps = {
    stroke: ink.grid,
    tick: { fill: ink.text, fontSize: 12 },
    tickLine: false,
    axisLine: { stroke: ink.grid },
  };
  const tooltip = <Tooltip content={<ChartTooltip xKey={x} pie={type === "pie"} />} cursor={{ fill: ink.grid, fillOpacity: 0.4, stroke: ink.axis }} />;
  const legend = multi ? (
    <Legend iconType="circle" iconSize={8} itemSorter={null} wrapperStyle={{ fontSize: 12, color: ink.text, paddingTop: 8 }}
      formatter={(v) => <span style={{ color: ink.text }}>{humanize(String(v))}</span>} />
  ) : null;
  const grid = <CartesianGrid stroke={ink.grid} vertical={horizontal} horizontal={!horizontal} />;
  const margin = { top: 12, right: 16, bottom: 4, left: 4 };

  let chart: JSX.Element;
  if (type === "pie") {
    const key = series[0];
    const total = data.reduce((s, d) => s + (Number(d[key]) || 0), 0);
    chart = (
      <PieChart>
        {tooltip}
        <Pie data={data} dataKey={key} nameKey={x} innerRadius="58%" outerRadius="88%" paddingAngle={1}
          startAngle={90} endAngle={-270}
          stroke={ink.surface} strokeWidth={2} isAnimationActive={false}>
          {data.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
        </Pie>
        <Legend layout="vertical" align="right" verticalAlign="middle" iconType="circle" iconSize={8} itemSorter={null}
          wrapperStyle={{ fontSize: 12 }}
          formatter={(v, entry) => {
            const val = Number((entry.payload as Record<string, unknown> | undefined)?.[key]) || 0;
            return (
              <span style={{ color: ink.text }}>
                {truncate(String(v), 22)} <b style={{ fontWeight: 600 }}>{total ? Math.round((val / total) * 100) : 0}%</b>
              </span>
            );
          }} />
      </PieChart>
    );
  } else if (type === "scatter") {
    chart = (
      <ScatterChart margin={margin}>
        {grid}
        <XAxis type="number" dataKey={x} name={humanize(x)} tickFormatter={tick} {...axisProps} />
        <YAxis type="number" dataKey={series[0]} name={humanize(series[0])} tickFormatter={tick} width={56} {...axisProps} />
        <Tooltip cursor={{ stroke: ink.axis }} content={({ active, payload }) =>
          active && payload?.length ? (
            <div className="chart-tip">
              {payload.map((p, i) => (
                <div className="chart-tip__row" key={i}>
                  <span className="chart-tip__name">{String(p.name)}</span>
                  <span className="chart-tip__value">{formatCell(p.value)}</span>
                </div>
              ))}
            </div>
          ) : null} />
        <Scatter data={data} fill={colors[0]} stroke={ink.surface} strokeWidth={2} isAnimationActive={false} />
      </ScatterChart>
    );
  } else if (type === "line" || type === "area") {
    const Chart = type === "line" ? LineChart : AreaChart;
    chart = (
      <Chart data={data} margin={margin}>
        {grid}
        <XAxis dataKey={x} tickFormatter={tick} minTickGap={16} {...axisProps} />
        <YAxis tickFormatter={tick} width={56} {...axisProps} />
        {tooltip}
        {legend}
        {series.map((s, i) =>
          type === "line" ? (
            <Line key={s} dataKey={s} type="monotone" stroke={colors[i]} strokeWidth={2} strokeLinecap="round"
              dot={data.length <= 24 ? { r: 4, fill: colors[i], stroke: ink.surface, strokeWidth: 2 } : false}
              activeDot={{ r: 5, stroke: ink.surface, strokeWidth: 2 }} isAnimationActive={false} />
          ) : (
            <Area key={s} dataKey={s} type="monotone" stroke={colors[i]} strokeWidth={2} fill={colors[i]}
              fillOpacity={0.12} isAnimationActive={false} />
          ),
        )}
      </Chart>
    );
  } else {
    chart = (
      <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={margin} barCategoryGap="20%" barGap={2}>
        {grid}
        {horizontal ? (
          <>
            <XAxis type="number" tickFormatter={tick} {...axisProps} />
            <YAxis type="category" dataKey={x} width={120} tickFormatter={(v) => truncate(String(v), 18)} interval={0} {...axisProps} />
          </>
        ) : (
          <>
            <XAxis dataKey={x} tickFormatter={tick} interval={0} {...axisProps} />
            <YAxis tickFormatter={tick} width={56} {...axisProps} />
          </>
        )}
        {tooltip}
        {legend}
        {series.map((s, i) => (
          <Bar key={s} dataKey={s} fill={colors[i]} maxBarSize={24} isAnimationActive={false}
            radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} />
        ))}
      </BarChart>
    );
  }

  return (
    <div className="chart" role="img" aria-label={`${type} chart of ${series.map(humanize).join(", ")} by ${humanize(x)}`}>
      {!multi && type !== "pie" && (
        <div className="chart__caption">{humanize(series[0])} by {humanize(x)}</div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {chart}
      </ResponsiveContainer>
    </div>
  );
}
