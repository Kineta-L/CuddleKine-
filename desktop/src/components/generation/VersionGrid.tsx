import type { Generation } from "../../api/client";

interface VersionGridProps {
  generations: Generation[];
  selectedId: number | null;
  imageUrl: (filePath: string) => string;
  onSelect: (id: number) => void;
  onConfirm: (id: number) => void;
  compactTitle?: string;
}

export default function VersionGrid({
  generations,
  selectedId,
  imageUrl,
  onSelect,
  onConfirm,
  compactTitle = "候选版本",
}: VersionGridProps) {
  if (generations.length === 0) {
    return (
      <div className="empty-state">
        <p>还没有生成版本，先从左侧选择模型并生成主视图。</p>
      </div>
    );
  }

  return (
    <section className="version-strip">
      <div className="strip-title">{compactTitle}</div>
      <div className="image-grid">
        {generations.map((generation) => (
          <div
            key={generation.id}
            className={`image-card ${selectedId === generation.id ? "selected" : ""}`}
            onClick={() => generation.file_path && onSelect(generation.id)}
          >
            {generation.file_path ? (
              <img src={imageUrl(generation.file_path)} alt={`候选 ${generation.id}`} />
            ) : (
              <div className="sample-placeholder small">
                <strong>无输出</strong>
                <span>{generation.error_message || "等待结果"}</span>
              </div>
            )}
            <div className="info">
              <span>{generation.provider}/{generation.provider_model || "-"}</span>
              <span>{generation.duration ? `${generation.duration}s` : "-"}</span>
              {generation.file_path && (
                <button
                  className="btn btn-outline btn-sm"
                  onClick={(event) => {
                    event.stopPropagation();
                    onConfirm(generation.id);
                  }}
                >
                  确认
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
