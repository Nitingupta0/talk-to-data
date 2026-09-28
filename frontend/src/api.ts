import type { Chat, ChatMode, ChatWithMessages, Dataset, DatasetDetail, StreamEvent } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* not JSON */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  health: () => request<{ ok: boolean; llm_configured: boolean; model: string }>("/api/health"),

  listDatasets: () => request<Dataset[]>("/api/datasets"),
  getDataset: (id: string, rows = 100) => request<DatasetDetail>(`/api/datasets/${id}?rows=${rows}`),
  deleteDataset: (id: string) => request<void>(`/api/datasets/${id}`, { method: "DELETE" }),
  uploadDatasets: (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request<Dataset[]>("/api/datasets", { method: "POST", body: form });
  },
  listSamples: () => request<{ name: string; size_kb: number }[]>("/api/samples"),
  loadSample: (name: string) => request<Dataset[]>(`/api/samples/${encodeURIComponent(name)}`, { method: "POST" }),

  listChats: () => request<Chat[]>("/api/chats"),
  getChat: (id: string) => request<ChatWithMessages>(`/api/chats/${id}`),
  createChat: (dataset_ids: string[] = []) =>
    request<ChatWithMessages>("/api/chats", { method: "POST", body: JSON.stringify({ dataset_ids }) }),
  updateChat: (id: string, patch: { title?: string; mode?: ChatMode }) =>
    request<Chat>(`/api/chats/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteChat: (id: string) => request<void>(`/api/chats/${id}`, { method: "DELETE" }),
  setChatDatasets: (id: string, dataset_ids: string[]) =>
    request<ChatWithMessages>(`/api/chats/${id}/datasets`, { method: "PUT", body: JSON.stringify({ dataset_ids }) }),

  /** POST a question and invoke `onEvent` for every server-sent event until the stream ends. */
  async ask(chatId: string, content: string, onEvent: (e: StreamEvent) => void, signal?: AbortSignal) {
    const res = await fetch(`${BASE}/api/chats/${chatId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
      signal,
    });
    if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const chunk = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const data = chunk
          .split("\n")
          .filter((l) => l.startsWith("data: "))
          .map((l) => l.slice(6))
          .join("\n");
        if (data) onEvent(JSON.parse(data) as StreamEvent);
      }
    }
  },
};
