import { Eye, FileSpreadsheet, Plus, Trash2 } from "lucide-react";
import type { Dataset } from "../types";
import { Dropzone } from "./Dropzone";

interface Props {
  datasets: Dataset[];
  attached: string[];
  uploading: boolean;
  onUpload: (files: File[]) => void;
  onAttach: (id: string) => void;
  onInspect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function Library({ datasets, attached, uploading, onUpload, onAttach, onInspect, onDelete }: Props) {
  return (
    <div className="library">
      <div className="sidebar__section-label">Data library</div>
      <div className="library__list">
        {datasets.map((d) => {
          const isAttached = attached.includes(d.id);
          return (
            <div key={d.id} className={`lib-item ${isAttached ? "is-attached" : ""}`}>
              <FileSpreadsheet size={15} />
              <button className="lib-item__main" onClick={() => onInspect(d.id)} title={`Inspect ${d.name}`}>
                <span className="lib-item__name">{d.name}</span>
                <span className="lib-item__meta">{d.rows.toLocaleString()} × {d.cols}</span>
              </button>
              <div className="lib-item__actions">
                {!isAttached && (
                  <button className="icon-btn" aria-label={`Add ${d.name} to chat`} title="Add to this chat" onClick={() => onAttach(d.id)}>
                    <Plus size={14} />
                  </button>
                )}
                <button className="icon-btn" aria-label="Inspect" title="Inspect" onClick={() => onInspect(d.id)}><Eye size={14} /></button>
                <button className="icon-btn icon-btn--danger" aria-label="Delete" title="Delete from library"
                  onClick={() => confirm(`Delete ${d.name} from your library? It will be detached from every chat.`) && onDelete(d.id)}>
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <Dropzone onFiles={onUpload} uploading={uploading} compact />
    </div>
  );
}
