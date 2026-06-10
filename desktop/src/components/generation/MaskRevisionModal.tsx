import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { Generation } from "../../api/client";
import { VIEW_LABELS } from "./labels";

interface MaskRevisionModalProps {
  generation: Generation;
  imageUrl: (filePath: string) => string;
  generating: boolean;
  onClose: () => void;
  onSubmit: (generation: Generation, maskDataUrl: string, prompt: string) => void;
}

export default function MaskRevisionModal({
  generation,
  imageUrl,
  generating,
  onClose,
  onSubmit,
}: MaskRevisionModalProps) {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement | null>(null);
  const maskRef = useRef<HTMLCanvasElement | null>(null);
  const drawingRef = useRef(false);
  const lastPointRef = useRef<{ x: number; y: number } | null>(null);
  const [prompt, setPrompt] = useState("");
  const [brushSize, setBrushSize] = useState(44);
  const [mode, setMode] = useState<"paint" | "erase">("paint");
  const [hasMask, setHasMask] = useState(false);

  function setupCanvases() {
    const img = imageRef.current;
    const overlay = overlayRef.current;
    const mask = maskRef.current;
    if (!img || !overlay || !mask) return;
    const width = img.naturalWidth || 1024;
    const height = img.naturalHeight || 1536;
    for (const canvas of [overlay, mask]) {
      canvas.width = width;
      canvas.height = height;
    }
    overlay.getContext("2d")?.clearRect(0, 0, width, height);
    const maskCtx = mask.getContext("2d");
    if (maskCtx) {
      maskCtx.fillStyle = "#000";
      maskCtx.fillRect(0, 0, width, height);
    }
    setHasMask(false);
  }

  function pointFromEvent(event: ReactPointerEvent<HTMLCanvasElement>) {
    const canvas = overlayRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * canvas.width,
      y: ((event.clientY - rect.top) / rect.height) * canvas.height,
    };
  }

  function drawTo(point: { x: number; y: number }) {
    const overlay = overlayRef.current;
    const mask = maskRef.current;
    const previous = lastPointRef.current || point;
    if (!overlay || !mask) return;

    const overlayCtx = overlay.getContext("2d");
    const maskCtx = mask.getContext("2d");
    if (!overlayCtx || !maskCtx) return;

    overlayCtx.lineCap = "round";
    overlayCtx.lineJoin = "round";
    overlayCtx.lineWidth = brushSize;
    overlayCtx.globalCompositeOperation = mode === "paint" ? "source-over" : "destination-out";
    overlayCtx.strokeStyle = "rgba(255, 76, 96, 0.48)";
    overlayCtx.beginPath();
    overlayCtx.moveTo(previous.x, previous.y);
    overlayCtx.lineTo(point.x, point.y);
    overlayCtx.stroke();
    overlayCtx.globalCompositeOperation = "source-over";

    maskCtx.lineCap = "round";
    maskCtx.lineJoin = "round";
    maskCtx.lineWidth = brushSize;
    maskCtx.globalCompositeOperation = "source-over";
    maskCtx.strokeStyle = mode === "paint" ? "#fff" : "#000";
    maskCtx.beginPath();
    maskCtx.moveTo(previous.x, previous.y);
    maskCtx.lineTo(point.x, point.y);
    maskCtx.stroke();
    lastPointRef.current = point;
    setHasMask(true);
  }

  function clearMask() {
    const overlay = overlayRef.current;
    const mask = maskRef.current;
    if (!overlay || !mask) return;
    overlay.getContext("2d")?.clearRect(0, 0, overlay.width, overlay.height);
    const maskCtx = mask.getContext("2d");
    if (maskCtx) {
      maskCtx.fillStyle = "#000";
      maskCtx.fillRect(0, 0, mask.width, mask.height);
    }
    setHasMask(false);
  }

  function submit() {
    const mask = maskRef.current;
    if (!mask || !hasMask) {
      alert("请先用画笔涂出需要修改的区域。");
      return;
    }
    onSubmit(generation, mask.toDataURL("image/png"), prompt);
  }

  return (
    <div className="modal-overlay mask-editor-overlay">
      <div className="modal-box mask-editor-modal">
        <div className="mask-editor-head">
          <div>
            <h3>画笔局部修版</h3>
            <p>当前视角：{VIEW_LABELS[generation.view_type] || generation.view_type} / Version #{generation.id}</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={onClose}>关闭</button>
        </div>

        <div className="mask-editor-grid">
          <div className="mask-canvas-wrap">
            <img ref={imageRef} src={imageUrl(generation.file_path || "")} alt="待修版视角" onLoad={setupCanvases} />
            <canvas
              ref={overlayRef}
              onPointerDown={(event) => {
                drawingRef.current = true;
                lastPointRef.current = pointFromEvent(event);
                if (lastPointRef.current) drawTo(lastPointRef.current);
                event.currentTarget.setPointerCapture(event.pointerId);
              }}
              onPointerMove={(event) => {
                if (!drawingRef.current) return;
                const point = pointFromEvent(event);
                if (point) drawTo(point);
              }}
              onPointerUp={(event) => {
                drawingRef.current = false;
                lastPointRef.current = null;
                event.currentTarget.releasePointerCapture(event.pointerId);
              }}
              onPointerLeave={() => {
                drawingRef.current = false;
                lastPointRef.current = null;
              }}
            />
            <canvas ref={maskRef} className="hidden-mask-canvas" />
          </div>

          <aside className="mask-editor-tools">
            <div className="form-group">
              <label>修改说明</label>
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="例如：只把左耳缩小一点，其他部位保持完全不变。"
              />
            </div>
            <div className="form-group">
              <label>画笔大小：{brushSize}px</label>
              <input
                type="range"
                min="12"
                max="120"
                value={brushSize}
                onChange={(event) => setBrushSize(Number(event.target.value))}
              />
            </div>
            <div className="mask-tool-row">
              <button className={`btn btn-sm ${mode === "paint" ? "btn-primary" : "btn-outline"}`} onClick={() => setMode("paint")}>画笔</button>
              <button className={`btn btn-sm ${mode === "erase" ? "btn-primary" : "btn-outline"}`} onClick={() => setMode("erase")}>橡皮</button>
              <button className="btn btn-outline btn-sm" onClick={clearMask}>清空</button>
            </div>
            <p className="dock-note">
              红色区域就是要修改的地方。未涂区域会在提示词里强制保持不变。
            </p>
            <button className="btn btn-primary mask-submit" onClick={submit} disabled={generating || !hasMask || !prompt.trim()}>
              {generating ? "生成中..." : "生成这个视角的修版"}
            </button>
          </aside>
        </div>
      </div>
    </div>
  );
}
