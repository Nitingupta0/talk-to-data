import { Check, MessageSquare, Pencil, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";
import { relativeTime } from "../format";
import type { Chat } from "../types";

interface Props {
  chats: Chat[];
  activeId: string | null;
  open: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
  footer: React.ReactNode;
}

export function Sidebar({ chats, activeId, open, onSelect, onNew, onRename, onDelete, onClose, footer }: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const commit = (id: string) => {
    if (draft.trim()) onRename(id, draft.trim());
    setEditing(null);
  };

  return (
    <>
      <div className={`scrim ${open ? "is-open" : ""}`} onClick={onClose} />
      <aside className={`sidebar ${open ? "is-open" : ""}`}>
        <div className="brand">
          <div className="brand__mark" aria-hidden>
            <svg viewBox="0 0 32 32" width="28" height="28"><rect width="32" height="32" rx="8" fill="currentColor" /><rect x="8" y="16" width="4" height="8" rx="1.5" fill="#fff" /><rect x="14" y="11" width="4" height="13" rx="1.5" fill="#fff" /><rect x="20" y="7" width="4" height="17" rx="1.5" fill="#fff" opacity=".7" /></svg>
          </div>
          <div>
            <div className="brand__name">Talk to Data</div>
            <div className="brand__tag">Answers you can verify</div>
          </div>
          <button className="icon-btn sidebar__close" onClick={onClose} aria-label="Close menu"><X size={18} /></button>
        </div>

        <button className="btn btn--primary btn--block" onClick={onNew}>
          <Plus size={16} /> New analysis
        </button>

        <div className="sidebar__section-label">Conversations</div>
        <nav className="chat-list">
          {chats.length === 0 && <div className="chat-list__empty">No conversations yet.</div>}
          {chats.map((c) => (
            <div key={c.id} className={`chat-item ${c.id === activeId ? "is-active" : ""}`}>
              {editing === c.id ? (
                <form className="chat-item__edit" onSubmit={(e) => { e.preventDefault(); commit(c.id); }}>
                  <input autoFocus value={draft} onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => e.key === "Escape" && setEditing(null)} onBlur={() => commit(c.id)} maxLength={120} />
                  <button type="submit" className="icon-btn" aria-label="Save"><Check size={14} /></button>
                </form>
              ) : (
                <>
                  <button className="chat-item__main" onClick={() => onSelect(c.id)}>
                    <MessageSquare size={15} />
                    <span className="chat-item__title">{c.title}</span>
                    <span className="chat-item__time">{relativeTime(c.updated_at)}</span>
                  </button>
                  <div className="chat-item__actions">
                    <button className="icon-btn" aria-label="Rename" onClick={() => { setEditing(c.id); setDraft(c.title); }}>
                      <Pencil size={13} />
                    </button>
                    <button className="icon-btn icon-btn--danger" aria-label="Delete"
                      onClick={() => confirm(`Delete “${c.title}”?`) && onDelete(c.id)}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </nav>
        <div className="sidebar__footer">{footer}</div>
      </aside>
    </>
  );
}
