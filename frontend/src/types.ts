export type Role = "metric" | "dimension" | "time" | "id" | "text";

export interface ColumnProfile {
  name: string;
  dtype: string;
  role: Role;
  nulls: number;
  null_pct: number;
  unique: number;
  samples: unknown[];
  stats?: Record<string, number | string | null>;
  top_values?: { value: unknown; count: number }[];
  is_month?: boolean;
}

export interface Dataset {
  id: string;
  name: string;
  sheet: string | null;
  created_at: number;
  rows: number;
  cols: number;
  profile: { rows: number; cols: number; columns: ColumnProfile[]; memory_kb: number };
  semantics: { metrics: string[]; dimensions: string[]; time: string[]; rules: string[] };
  insights: { summary: string; suggestions: string[] } | null;
}

export interface TableData {
  columns: string[];
  rows: unknown[][];
  total_rows: number;
  truncated?: boolean;
}

export interface DatasetDetail extends Dataset {
  preview: TableData;
}

export type ChartType = "bar" | "line" | "area" | "pie" | "scatter";

export interface ChartSpec {
  type: ChartType;
  x: string;
  series: string[];
  x_label: string;
  y_label: string;
  time_x: boolean;
  alternatives: ChartType[];
  data: Record<string, string | number | null>[];
}

export interface ResultBlock {
  source: string;
  kind: "table" | "scalar" | "empty" | "error";
  narrative?: string;
  table?: TableData | null;
  scalar?: { value: unknown; label: string };
  chart?: ChartSpec | null;
  code?: string;
  attempts: number;
  error?: string;
  warnings: string[];
  citation?: { rows_scanned: number; columns_used: string[]; sources: string[] };
}

export type MessageKind = "answer" | "clarify" | "respond" | "error" | "welcome";

export interface Message {
  id: string;
  chat_id: string;
  role: "user" | "assistant";
  created_at: number;
  content: string;
  kind?: MessageKind;
  question?: string;
  intent?: string;
  mode?: "single" | "separate" | "merge";
  results?: ResultBlock[];
  follow_ups?: string[];
  duration_ms?: number;
  dataset_id?: string;
}

export type ChatMode = "auto" | "separate" | "merge";

export interface Chat {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  dataset_ids: string[];
  mode: ChatMode;
}

export interface ChatWithMessages extends Chat {
  messages: Message[];
}

export interface StatusEvent {
  stage: "plan" | "code" | "run" | "repair" | "explain";
  label: string;
  source: string | null;
}

export type StreamEvent =
  | { type: "user_message"; message: Message }
  | { type: "assistant_message"; message: Message }
  | { type: "chat"; chat: Chat }
  | ({ type: "status" } & StatusEvent)
  | { type: "done" };
