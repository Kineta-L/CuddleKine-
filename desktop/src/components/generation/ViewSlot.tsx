import type { Generation } from "../../api/client";

interface ViewSlotProps {
  label: string;
  generation?: Generation;
  imageUrl: (filePath: string) => string;
  onMaskEdit: (generation: Generation) => void;
}

export default function ViewSlot({ label, generation, imageUrl, onMaskEdit }: ViewSlotProps) {
  return (
    <div className={`view-slot ${generation?.file_path ? "has-image" : ""}`}>
      <div className="view-label">{label}</div>
      {generation?.file_path ? (
        <>
          <img src={imageUrl(generation.file_path)} alt={label} />
          <button className="btn btn-outline btn-sm view-mask-btn" onClick={() => onMaskEdit(generation)}>
            画笔修版
          </button>
        </>
      ) : (
        <span>待生成</span>
      )}
    </div>
  );
}
