import { useEffect, useState } from "react";
import {
  providersApi,
  settingsApi,
  type AppSettings,
  type AppSettingsUpdate,
  type ProviderInfo,
} from "../../api/client";
import { getErrorMessage } from "../../utils/errors";
import CapabilityChips from "./CapabilityChips";
import ProviderConfigCard from "./ProviderConfigCard";

interface SettingsModalProps {
  onClose: () => void;
  onSaved: () => void;
}

export default function SettingsModal({ onClose, onSaved }: SettingsModalProps) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [openaiKey, setOpenaiKey] = useState("");
  const [replicateToken, setReplicateToken] = useState("");
  const [agnesKey, setAgnesKey] = useState("");
  const [cosSecretId, setCosSecretId] = useState("");
  const [cosSecretKey, setCosSecretKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([settingsApi.get(), providersApi.list()])
      .then(([nextSettings, nextProviders]) => {
        setSettings(nextSettings);
        setProviders(nextProviders);
        setError("");
      })
      .catch((error: unknown) => setError(getErrorMessage(error, "设置加载失败")));
  }, []);

  if (!settings) {
    return (
      <div className="modal-overlay">
        <div className="modal-box settings-modal">
          <h3>程序设置</h3>
          <div className="loading">加载中...</div>
          <div className="modal-actions">
            <button className="btn btn-outline" onClick={onClose}>关闭</button>
          </div>
        </div>
      </div>
    );
  }

  const currentProvider = providers.find((provider) => provider.id === settings.default_provider);
  const models = currentProvider?.models || [];
  const providerById = (id: string) => providers.find((provider) => provider.id === id);
  const openai = providerById("openai");
  const replicate = providerById("replicate");
  const agnes = providerById("agnes");
  const comfyui = providerById("comfyui");

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const payload: AppSettingsUpdate = { ...settings };
      delete payload.openai_configured;
      delete payload.replicate_configured;
      delete payload.settings_path;
      if (openaiKey.trim()) payload.openai_api_key = openaiKey.trim();
      if (replicateToken.trim()) payload.replicate_api_token = replicateToken.trim();
      if (agnesKey.trim()) payload.agnes_api_key = agnesKey.trim();
      if (cosSecretId.trim()) payload.cos_secret_id = cosSecretId.trim();
      if (cosSecretKey.trim()) payload.cos_secret_key = cosSecretKey.trim();
      const next = await settingsApi.update(payload);
      setSettings(next);
      setOpenaiKey("");
      setReplicateToken("");
      setAgnesKey("");
      setCosSecretId("");
      setCosSecretKey("");
      onSaved();
      onClose();
    } catch (error: unknown) {
      setError(getErrorMessage(error, "保存失败"));
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
                  onChange={(event) => setSettings({ ...settings, default_provider: event.target.value, default_model: "" })}
                >
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name}{provider.configured ? "" : "（未配置）"}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>默认模型</label>
                <select
                  value={settings.default_model}
                  onChange={(event) => setSettings({ ...settings, default_model: event.target.value })}
                >
                  <option value="">自动选择</option>
                  {models.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}
                </select>
              </div>
            </div>
            <div className="settings-quality-row">
              {["draft", "sample", "final"].map((quality) => (
                <button
                  key={quality}
                  className={settings.default_quality === quality ? "active" : ""}
                  onClick={() => setSettings({ ...settings, default_quality: quality })}
                >
                  {quality === "draft" ? "草稿" : quality === "sample" ? "样品图" : "最终确认"}
                </button>
              ))}
            </div>
            <label className="settings-check settings-check-strong">
              <input
                type="checkbox"
                checked={settings.transparent_background}
                onChange={(event) => setSettings({ ...settings, transparent_background: event.target.checked })}
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
                onChange={(event) => setSettings({ ...settings, comfyui_base_url: event.target.value })}
              />
            </div>
            <div className="form-group">
              <label>ComfyUI 输入目录</label>
              <input
                value={settings.comfyui_input_dir}
                onChange={(event) => setSettings({ ...settings, comfyui_input_dir: event.target.value })}
              />
            </div>
          </section>

          <section className="settings-card settings-card-wide">
            <div className="settings-card-head">
              <h4>Tencent COS image bridge</h4>
              <span className={`settings-pill ${settings.cos_configured ? "ok" : "bad"}`}>
                {settings.cos_configured ? "configured" : "required for Agnes img2img"}
              </span>
            </div>
            <p className="settings-card-copy">
              Uploads local reference images to your private COS bucket and sends Agnes a temporary signed URL.
              Keep the bucket private; the URL expires automatically.
            </p>
            <div className="form-row">
              <div className="form-group">
                <label>COS Bucket</label>
                <input
                  value={settings.cos_bucket}
                  placeholder="cuddlekine-images-1438398703"
                  onChange={(event) => setSettings({ ...settings, cos_bucket: event.target.value })}
                />
              </div>
              <div className="form-group">
                <label>COS Region</label>
                <input
                  value={settings.cos_region}
                  placeholder="ap-guangzhou"
                  onChange={(event) => setSettings({ ...settings, cos_region: event.target.value })}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>SecretId</label>
                <input
                  type="password"
                  value={cosSecretId}
                  placeholder="Saved locally; enter a new value to replace"
                  onChange={(event) => setCosSecretId(event.target.value)}
                />
              </div>
              <div className="form-group">
                <label>SecretKey</label>
                <input
                  type="password"
                  value={cosSecretKey}
                  placeholder="Saved locally; enter a new value to replace"
                  onChange={(event) => setCosSecretKey(event.target.value)}
                />
              </div>
            </div>
            <div className="form-group">
              <label>Signed URL expires in seconds</label>
              <input
                value={settings.cos_url_expire_seconds}
                placeholder="3600"
                onChange={(event) => setSettings({ ...settings, cos_url_expire_seconds: event.target.value })}
              />
            </div>
          </section>

          <section className="settings-card settings-card-wide">
            <div className="settings-card-head">
              <h4>模型清单与能力</h4>
              <span className="settings-pill">{providers.length} providers</span>
            </div>
            <div className="provider-table">
              {providers.map((provider) => (
                <div key={provider.id} className="provider-row">
                  <div>
                    <strong>{provider.name}</strong>
                    <span>{provider.models?.map((model) => model.name).join(" / ") || "无模型列表"}</span>
                  </div>
                  <CapabilityChips provider={provider} compact />
                  <em className={provider.configured ? "ok" : "bad"}>{provider.configured ? "已配置" : "未配置"}</em>
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
            {saving ? "保存中..." : "保存设置"}
          </button>
        </div>
      </div>
    </div>
  );
}
