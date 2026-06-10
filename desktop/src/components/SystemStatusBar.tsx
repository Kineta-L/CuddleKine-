import { useEffect, useState } from "react";
import { statusApi, type SystemStatus } from "../api/client";
import SettingsModal from "./settings/SettingsModal";
import { getErrorMessage } from "../utils/errors";

export default function SystemStatusBar() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [startingComfyUI, setStartingComfyUI] = useState(false);
  const [message, setMessage] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const nextStatus = await statusApi.get();
      setStatus(nextStatus);
      setError("");
      if (nextStatus.comfyui.status === "ok") setMessage("");
    } catch (e: unknown) {
      setStatus(null);
      setError(getErrorMessage(e, "后端未连接"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const startComfyUI = async () => {
    setStartingComfyUI(true);
    try {
      const result = await statusApi.startComfyUI();
      setMessage(result.message);
      for (let i = 0; i < 4; i += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 5000));
        await loadStatus();
      }
    } catch (e: unknown) {
      setMessage(getErrorMessage(e, "启动 ComfyUI 失败"));
    } finally {
      setStartingComfyUI(false);
    }
  };

  const backendOk = status?.backend.status === "ok";
  const comfyuiOk = status?.comfyui.status === "ok";
  const provider = status?.generation.provider || "-";

  return (
    <div className="system-status" title={status ? `ComfyUI: ${status.comfyui.dir}` : error}>
      <StatusPill ok={backendOk && !error} label="后端" value={error ? "未连接" : "已连接"} />
      <StatusPill ok={comfyuiOk} label="ComfyUI" value={status ? (comfyuiOk ? "在线" : "离线") : "-"} />
      <span className="status-meta">Provider: {provider}</span>
      {status && !comfyuiOk && status.comfyui.dir_exists && (
        <button className="status-refresh" onClick={startComfyUI} disabled={startingComfyUI}>
          {startingComfyUI ? "启动中" : "启动 ComfyUI"}
        </button>
      )}
      {status && (!status.comfyui.dir_exists || !status.comfyui.input_dir_exists) && (
        <span className="status-warning">
          {!status.comfyui.dir_exists ? "ComfyUI 目录不存在" : "ComfyUI input 目录不存在"}
        </span>
      )}
      {message && <span className="status-message">{message}</span>}
      <button className="status-refresh" onClick={() => setSettingsOpen(true)}>
        设置
      </button>
      <button className="status-refresh" onClick={loadStatus} disabled={loading}>
        {loading ? "检测中" : "重试"}
      </button>
      {settingsOpen && (
        <SettingsModal
          onClose={() => setSettingsOpen(false)}
          onSaved={() => {
            loadStatus();
            setMessage("设置已保存");
          }}
        />
      )}
    </div>
  );
}

function StatusPill({ ok, label, value }: { ok: boolean; label: string; value: string }) {
  return (
    <span className={`status-pill ${ok ? "ok" : "bad"}`}>
      {label}: {value}
    </span>
  );
}
