import { AlertTriangle, FileSpreadsheet, Menu, Moon, Plus, Sun, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Composer } from "./components/Composer";
import { Dropzone } from "./components/Dropzone";
import { Inspector } from "./components/Inspector";
import { Library } from "./components/Library";
import { MessageView } from "./components/MessageView";
import { Onboarding } from "./components/Onboarding";
import { Progress } from "./components/Progress";
import { Sidebar } from "./components/Sidebar";
import { useTheme } from "./theme";
import type { Chat, ChatMode, ChatWithMessages, Dataset, Message, StatusEvent } from "./types";

export default function App() {
  const { theme, toggle } = useTheme();
  const [llmReady, setLlmReady] = useState<boolean | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [samples, setSamples] = useState<{ name: string; size_kb: number }[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [chat, setChat] = useState<ChatWithMessages | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<StatusEvent | null>(null);
  const [uploading, setUploading] = useState(false);
  const [inspect, setInspect] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fail = (e: unknown) => setError(e instanceof Error ? e.message : String(e));
  const refreshChats = useCallback(() => api.listChats().then(setChats).catch(fail), []);

  useEffect(() => {
    api.health().then((h) => setLlmReady(h.llm_configured)).catch(() => setLlmReady(null));
    api.listDatasets().then(setDatasets).catch(fail);
    api.listSamples().then(setSamples).catch(() => undefined);
    api.listChats().then((list) => {
      setChats(list);
      if (list.length) api.getChat(list[0].id).then(setChat).catch(fail);
    }).catch(fail);
  }, []);

  // Keep the newest content in view.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [chat?.messages.length, status, chat?.id]);

  const openChat = async (id: string) => {
    setSidebarOpen(false);
    if (busy || id === chat?.id) return;
    try {
      setChat(await api.getChat(id));
    } catch (e) {
      fail(e);
    }
  };

  const newChat = () => {
    if (busy) return;
    setChat(null);
    setSidebarOpen(false);
  };

  const ensureChat = async (): Promise<ChatWithMessages> => {
    if (chat) return chat;
    const created = await api.createChat();
    setChat(created);
    return created;
  };

  const attach = async (ids: string[]) => {
    try {
      const c = await ensureChat();
      const next = await api.setChatDatasets(c.id, [...c.dataset_ids, ...ids.filter((i) => !c.dataset_ids.includes(i))]);
      setChat(next);
      setAddOpen(false);
      refreshChats();
    } catch (e) {
      fail(e);
    }
  };

  const detach = async (id: string) => {
    if (!chat) return;
    try {
      setChat(await api.setChatDatasets(chat.id, chat.dataset_ids.filter((d) => d !== id)));
    } catch (e) {
      fail(e);
    }
  };

  const ingest = async (load: () => Promise<Dataset[]>) => {
    setUploading(true);
    setError(null);
    try {
      const created = await load();
      setDatasets((prev) => [...created, ...prev.filter((p) => !created.some((c) => c.id === p.id))]);
      await attach(created.map((d) => d.id));
    } catch (e) {
      fail(e);
    } finally {
      setUploading(false);
    }
  };

  const deleteDataset = async (id: string) => {
    try {
      await api.deleteDataset(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
      if (inspect === id) setInspect(null);
      if (chat?.dataset_ids.includes(id)) setChat(await api.getChat(chat.id));
    } catch (e) {
      fail(e);
    }
  };

  const renameChat = async (id: string, title: string) => {
    try {
      const updated = await api.updateChat(id, { title });
      setChats((prev) => prev.map((c) => (c.id === id ? updated : c)));
      if (chat?.id === id) setChat({ ...chat, title: updated.title });
    } catch (e) {
      fail(e);
    }
  };

  const deleteChat = async (id: string) => {
    try {
      await api.deleteChat(id);
      setChats((prev) => prev.filter((c) => c.id !== id));
      if (chat?.id === id) setChat(null);
    } catch (e) {
      fail(e);
    }
  };

  const setMode = async (mode: ChatMode) => {
    if (!chat) return;
    setChat({ ...chat, mode });
    api.updateChat(chat.id, { mode }).catch(fail);
  };

  const ask = async (text: string) => {
    if (!chat || busy) return;
    const chatId = chat.id;
    const temp: Message = { id: `tmp-${Date.now()}`, chat_id: chatId, role: "user", content: text, created_at: Date.now() / 1000 };
    setChat((c) => (c ? { ...c, messages: [...c.messages, temp] } : c));
    setBusy(true);
    setStatus(null);
    setError(null);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      await api.ask(chatId, text, (ev) => {
        if (ev.type === "user_message") {
          setChat((c) => (c && c.id === chatId ? { ...c, messages: c.messages.map((m) => (m.id === temp.id ? ev.message : m)) } : c));
        } else if (ev.type === "status") {
          setStatus(ev);
        } else if (ev.type === "chat") {
          setChat((c) => (c && c.id === chatId ? { ...c, title: ev.chat.title } : c));
          setChats((prev) => [ev.chat, ...prev.filter((p) => p.id !== ev.chat.id)]);
        } else if (ev.type === "assistant_message") {
          setChat((c) => (c && c.id === chatId ? { ...c, messages: [...c.messages, ev.message] } : c));
        }
      }, ctrl.signal);
    } catch (e) {
      if ((e as Error).name !== "AbortError") fail(e);
    } finally {
      setBusy(false);
      setStatus(null);
      abortRef.current = null;
      refreshChats();
    }
  };

  const stop = () => {
    abortRef.current?.abort();
    // The server still finishes and saves the answer; pick it up shortly.
    if (chat) setTimeout(() => api.getChat(chat.id).then((c) => setChat((cur) => (cur?.id === c.id ? c : cur))), 1500);
  };

  const attached = chat ? datasets.filter((d) => chat.dataset_ids.includes(d.id)) : [];
  const unattached = datasets.filter((d) => !chat?.dataset_ids.includes(d.id));
  const lastAssistant = chat ? [...chat.messages].reverse().find((m) => m.role === "assistant")?.id : undefined;

  return (
    <div className="app">
      <Sidebar
        chats={chats}
        activeId={chat?.id ?? null}
        open={sidebarOpen}
        onSelect={openChat}
        onNew={newChat}
        onRename={renameChat}
        onDelete={deleteChat}
        onClose={() => setSidebarOpen(false)}
        footer={
          <Library
            datasets={datasets}
            attached={chat?.dataset_ids ?? []}
            uploading={uploading}
            onUpload={(f) => ingest(() => api.uploadDatasets(f))}
            onAttach={(id) => attach([id])}
            onInspect={setInspect}
            onDelete={deleteDataset}
          />
        }
      />

      <main className="main">
        <header className="topbar">
          <button className="icon-btn topbar__menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={20} /></button>
          <div className="topbar__title">{chat?.title ?? "New analysis"}</div>
          <div className="topbar__data">
            {attached.map((d) => (
              <span key={d.id} className="data-chip">
                <button className="data-chip__main" onClick={() => setInspect(d.id)} title="Inspect columns">
                  <FileSpreadsheet size={13} />
                  <span>{d.name}</span>
                </button>
                <button className="data-chip__x" onClick={() => detach(d.id)} aria-label={`Remove ${d.name}`} disabled={busy}><X size={12} /></button>
              </span>
            ))}
            {attached.length > 0 && (
              <div className="popover-anchor">
                <button className="btn btn--ghost btn--sm" onClick={() => setAddOpen((o) => !o)}><Plus size={14} /> Add data</button>
                {addOpen && (
                  <>
                    <div className="popover-scrim" onClick={() => setAddOpen(false)} />
                    <div className="popover">
                      {unattached.length > 0 && <div className="popover__label">From your library</div>}
                      {unattached.map((d) => (
                        <button key={d.id} className="popover__item" onClick={() => attach([d.id])}>
                          <FileSpreadsheet size={14} /> <span>{d.name}</span> <small>{d.rows.toLocaleString()} rows</small>
                        </button>
                      ))}
                      <Dropzone compact uploading={uploading} onFiles={(f) => ingest(() => api.uploadDatasets(f))} />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
          <button className="icon-btn" onClick={toggle} aria-label="Toggle theme" title="Toggle theme">
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </header>

        {llmReady === false && (
          <div className="banner">
            <AlertTriangle size={16} /> No language model configured — add <code>GROQ_API_KEY</code> to <code>.env</code> and restart the backend.
            You can still upload and inspect data.
          </div>
        )}
        {error && (
          <div className="banner banner--error" role="alert">
            <AlertTriangle size={16} /> {error}
            <button className="icon-btn" onClick={() => setError(null)} aria-label="Dismiss"><X size={14} /></button>
          </div>
        )}

        <div className="scroll" ref={scrollRef}>
          {!chat || attached.length === 0 ? (
            <div className="content">
              {chat && chat.messages.length > 0 && (
                <div className="messages">
                  {chat.messages.map((m) => (
                    <MessageView key={m.id} message={m} theme={theme} onAsk={ask} busy isLatest={false} />
                  ))}
                </div>
              )}
              <Onboarding
                datasets={datasets}
                samples={samples}
                uploading={uploading}
                onUpload={(f) => ingest(() => api.uploadDatasets(f))}
                onSample={(n) => ingest(() => api.loadSample(n))}
                onAttach={(id) => attach([id])}
              />
            </div>
          ) : (
            <div className="content messages">
              {chat.messages.map((m) => (
                <MessageView key={m.id} message={m} theme={theme} onAsk={ask} busy={busy} isLatest={m.id === lastAssistant} />
              ))}
              {busy && (
                <div className="msg msg--assistant">
                  <div className="avatar avatar--pulse" aria-hidden />
                  <div className="msg__body"><Progress status={status} /></div>
                </div>
              )}
            </div>
          )}
        </div>

        <Composer
          disabled={!chat || attached.length === 0}
          busy={busy}
          placeholder={attached.length ? `Ask about ${attached.map((d) => d.name).join(", ")}…` : "Add a dataset to start asking questions"}
          multiFile={attached.length > 1}
          mode={chat?.mode ?? "auto"}
          onMode={setMode}
          onSend={ask}
          onStop={stop}
        />
      </main>

      {inspect && <Inspector datasetId={inspect} onClose={() => setInspect(null)} />}
    </div>
  );
}
