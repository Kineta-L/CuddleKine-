import { useEffect, useState } from "react";
import {
  providersApi,
  settingsApi,
  statusApi,
  type AppSettings,
  type ProviderInfo,
  type SystemStatus,
} from "../api/client";

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
    } catch (e: any) {
      setStatus(null);
      setError(e.message || "后端未连接");
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
    } catch (e: any) {
      setMessage(e.message || "启动 ComfyUI 失败");
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

function SettingsModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [openaiKey, setOpenaiKey] = useState("");
  const [replicateToken, setReplicateToken] = useState("");
  const [agnesKey, setAgnesKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([settingsApi.get(), providersApi.list()])
      .then(([nextSettings, nextProviders]) => {
        setSettings(nextSettings);
        setProviders(nextProviders);
      })
      .catch((e: any) => setError(e.message || "设置加载失败"));
  }, []);

  if (!settings) {
    return (
      <div className="modal-overlay">
        <div className="modal-box settings-modal">
          <h3>程序设置</h3>
          <div className="loading">加载中</div>
          <div className="modal-actions">
            <button className="btn btn-outline" onClick={onClose}>关闭</button>
          </div>
        </div>
      </div>
    );
  }

  const currentProvider = providers.find((p) => p.id === settings.default_provider);
  const models = currentProvider?.models || [];
  const providerById = (id: string) => providers.find((p) => p.id === id);
  const openai = providerById("openai");
  const replicate = providerById("replicate");
  const agnes = providerById("agnes");
  const comfyui = providerById("comfyui");

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const payload: any = { ...settings };
      delete payload.openai_configured;
      delete payload.replicate_configured;
      delete payload.settings_path;
      if (openaiKey.trim()) payload.openai_api_key = openaiKey.trim();
      if (replicateToken.trim()) payload.replicate_api_token = replicateToken.trim();
      if (agnesKey.trim()) payload.agnes_api_key = agnesKey.trim();
      const next = await settingsApi.update(payload);
      setSettings(next);
      setOpenaiKey("");
      setReplicateToken("");
      setAgnesKey("");
      onSaved();
      onClose();
    } catch (e: any) {
      setError(e.message || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-box settings-modal">
        <div className="settings-header">
          <div>
            <div className="studio-kicker">CuddleKine Control Center</div>
            <h3>设置中心</h3>
            <p>配置默认生成行为、第三方模型连接和本地 ComfyUI 路径。</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={onClose}>关闭</button>
        </div>
        {error && <div className="settings-error">{error}</div>}

        <div className="settings-bento">
          <section className="settings-card settings-card-large">
            <div className="settings-card-head">
              <h4>默认生成行为</h4>
              <span className="settings-pill">全局默认</span>
            </div>
            <div className="settings-summary-grid">
              <div><strong>{currentProvider?.name || settings.default_provider}</strong><span>默认服务</span></div>
              <div><strong>{settings.default_model || "自动选择"}</strong><span>默认模型</span></div>
              <div><strong>{settings.default_quality || "sample"}</strong><span>默认质量</span></div>
              <div><strong>{settings.transparent_background ? "开启" : "关闭"}</strong><span>透明背景</span></div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>默认生成服务</label>
                <select
                  value={settings.default_provider}
                  onChange={(e) => setSettings({ ...settings, default_provider: e.target.value, default_model: "" })}
                >
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}{p.configured ? "" : "（未配置）"}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>默认模型</label>
                <select
                  value={settings.default_model}
                  onChange={(e) => setSettings({ ...settings, default_model: e.target.value })}
                >
                  <option value="">自动选择</option>
                  {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
            </div>
            <div className="settings-quality-row">
              {["draft", "sample", "final"].map((q) => (
                <button
                  key={q}
                  className={settings.default_quality === q ? "active" : ""}
                  onClick={() => setSettings({ ...settings, default_quality: q })}
                >
                  {q === "draft" ? "草稿" : q === "sample" ? "样品图" : "最终确认"}
                </button>
              ))}
            </div>
            <label className="settings-check settings-check-strong">
              <input
                type="checkbox"
                checked={settings.transparent_background}
                onChange={(e) => setSettings({ ...settings, transparent_background: e.target.checked })}
              />
              默认要求透明背景输出
            </label>
          </section>

          <ProviderConfigCard
            provider={openai}
            title="OpenAI"
            status={settings.openai_configured}
            bestFor="最高质量客户样品图、参考图还原、透明背景"
            cost="按 OpenAI API 计费"
            secretLabel="OpenAI API Key"
            secretPlaceholder="sk-..."
            secretValue={openaiKey}
            onSecretChange={setOpenaiKey}
          />

          <ProviderConfigCard
            provider={replicate}
            title="Replicate"
            status={settings.replicate_configured}
            bestFor="云端备用模型、Flux/SDXL 草稿、模型扩展"
            cost="按 Replicate 余额计费"
            secretLabel="Replicate API Token"
            secretPlaceholder="r8_..."
            secretValue={replicateToken}
            onSecretChange={setReplicateToken}
          />

          <ProviderConfigCard
            provider={agnes}
            title="Agnes"
            status={settings.agnes_configured}
            bestFor="低成本云端图片测试、文生图草稿、模型效果对比"
            cost="约 $0.008 / image，按 Agnes 账户计费"
            secretLabel="Agnes API Key"
            secretPlaceholder="Agnes API Key"
            secretValue={agnesKey}
            onSecretChange={setAgnesKey}
          />

          <section className="settings-card">
            <div className="settings-card-head">
              <h4>ComfyUI 本地服务</h4>
              <span className={`settings-pill ${comfyui?.configured ? "ok" : "bad"}`}>
                {comfyui?.configured ? "可用" : "需检查"}
              </span>
            </div>
            <CapabilityChips provider={comfyui} />
            <p className="settings-card-copy">适合低成本草稿和本机离线工作流。参考图会复制到输入目录供 LoadImage 节点读取。</p>
            <div className="form-group">
              <label>ComfyUI API 地址</label>
              <input
                value={settings.comfyui_base_url}
                onChange={(e) => setSettings({ ...settings, comfyui_base_url: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>ComfyUI 输入目录</label>
              <input
                value={settings.comfyui_input_dir}
                onChange={(e) => setSettings({ ...settings, comfyui_input_dir: e.target.value })}
              />
            </div>
          </section>

          <section className="settings-card settings-card-wide">
            <div className="settings-card-head">
              <h4>模型清单与能力</h4>
              <span className="settings-pill">{providers.length} providers</span>
            </div>
            <div className="provider-table">
              {providers.map((p) => (
                <div key={p.id} className="provider-row">
                  <div>
                    <strong>{p.name}</strong>
                    <span>{p.models?.map((m) => m.name).join(" / ") || "无模型列表"}</span>
                  </div>
                  <CapabilityChips provider={p} compact />
                  <em className={p.configured ? "ok" : "bad"}>{p.configured ? "已配置" : "未配置"}</em>
                </div>
              ))}
            </div>
          </section>

          <section className="settings-card settings-card-wide">
            <div className="settings-card-head">
              <h4>配置文件与安全</h4>
              <span className="settings-pill">Local</span>
            </div>
            <p className="settings-card-copy">
              API Key 只保存在本机配置文件中，接口不会把密钥明文返回到前端。更换密钥时直接填写新值并保存即可。
            </p>
            <div className="settings-path">配置文件：{settings.settings_path}</div>
          </section>
        </div>

        <div className="modal-actions">
          <button className="btn btn-outline" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? "保存中" : "保存设置"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ProviderConfigCard({
  provider,
  title,
  status,
  bestFor,
  cost,
  secretLabel,
  secretPlaceholder,
  secretValue,
  onSecretChange,
}: {
  provider?: ProviderInfo;
  title: string;
  status: boolean;
  bestFor: string;
  cost: string;
  secretLabel: string;
  secretPlaceholder: string;
  secretValue: string;
  onSecretChange: (value: string) => void;
}) {
  return (
    <section className="settings-card">
      <div className="settings-card-head">
        <h4>{title}</h4>
        <span className={`settings-pill ${status ? "ok" : "bad"}`}>
          {status ? "已配置" : "未配置"}
        </span>
      </div>
      <CapabilityChips provider={provider} />
      <p className="settings-card-copy">{bestFor}</p>
      <div className="settings-cost">{cost}</div>
      <div className="form-group">
        <label>{secretLabel}</label>
        <input
          type="password"
          value={secretValue}
          placeholder={status ? "已保存，填入新值可覆盖" : secretPlaceholder}
          onChange={(e) => onSecretChange(e.target.value)}
        />
      </div>
    </section>
  );
}

function CapabilityChips({ provider, compact = false }: { provider?: ProviderInfo; compact?: boolean }) {
  const capabilities = [
    ["文生图", provider?.supports_text_to_image],
    ["图生图", provider?.supports_image_to_image],
    ["局部修改", provider?.supports_inpaint],
    ["透明背景", provider?.supports_transparent_background],
  ];
  return (
    <div className={`capability-chips ${compact ? "compact" : ""}`}>
      {capabilities.map(([label, enabled]) => (
        <span key={label as string} className={enabled ? "on" : "off"}>{label as string}</span>
      ))}
    </div>
  );
}
