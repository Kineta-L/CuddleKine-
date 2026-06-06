import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  briefsApi,
  materialsApi,
  ordersApi,
  workflowApi,
  type Brief,
  type Material,
  type Order,
} from "../api/client";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  material_imported: "素材已导入",
  brief_pending: "待确认 brief",
  brief_confirmed: "brief 已确认",
  generating: "生成中",
  reviewing: "审核中",
  exported: "已导出",
  archived: "已归档",
};

const MATERIAL_TYPES = [
  { value: "reference", label: "参考图" },
  { value: "photo", label: "照片" },
  { value: "sketch", label: "手绘图" },
  { value: "chat_screenshot", label: "聊天截图" },
  { value: "text", label: "文字素材" },
];

const BRIEF_FIELDS = [
  ["order_intent", "订单意图"],
  ["source_type", "素材类型"],
  ["toy_category", "玩具品类"],
  ["character_identity", "角色身份"],
  ["target_height", "成品高度"],
  ["body_proportions", "身体比例"],
  ["head_features", "头部特征"],
  ["face_features", "面部特征"],
  ["clothing", "服装结构"],
  ["colors", "颜色方案"],
  ["materials", "材质工艺"],
  ["accessories", "配件"],
  ["key_features_to_preserve", "必须保留"],
  ["allowed_simplifications", "允许简化"],
  ["forbidden_changes", "禁止改动"],
] as const;

export default function OrderDetail() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const id = Number(orderId);

  const [order, setOrder] = useState<Order | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [briefs, setBriefs] = useState<Brief[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [briefForm, setBriefForm] = useState<Record<string, string>>({});
  const [promptPreview, setPromptPreview] = useState("");

  useEffect(() => {
    if (id) loadAll(id);
  }, [id]);

  const latestBrief = briefs[0] || null;

  useEffect(() => {
    if (!latestBrief?.structured_content) {
      setBriefForm({});
      return;
    }
    const parsed = safeJson<Record<string, unknown>>(latestBrief.structured_content, {});
    const next: Record<string, string> = {};
    for (const [key] of BRIEF_FIELDS) {
      next[key] = stringifyValue(parsed[key]);
    }
    setBriefForm(next);
  }, [latestBrief?.id]);

  const questions = useMemo(
    () => safeJson<string[]>(latestBrief?.pending_questions || "[]", []),
    [latestBrief?.pending_questions],
  );
  const risks = useMemo(
    () => safeJson<string[]>(latestBrief?.risk_notes || "[]", []),
    [latestBrief?.risk_notes],
  );
  const missingItems = useMemo(
    () => safeJson<{ field: string; description: string; reason?: string }[]>(
      latestBrief?.missing_info || "[]",
      [],
    ),
    [latestBrief?.missing_info],
  );

  async function loadAll(orderIdToLoad: number) {
    setLoading(true);
    try {
      const [loadedOrder, loadedMaterials, loadedBriefs] = await Promise.all([
        ordersApi.get(orderIdToLoad),
        materialsApi.list(orderIdToLoad),
        briefsApi.list(orderIdToLoad),
      ]);
      setOrder(loadedOrder);
      setMaterials(loadedMaterials);
      setBriefs(loadedBriefs);
    } catch (error: any) {
      alert(`加载失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>, type: string) {
    if (!order || !event.target.files?.length) return;
    setUploading(true);
    try {
      await materialsApi.upload(order.id, event.target.files[0], type);
      await loadAll(order.id);
    } catch (error: any) {
      alert(`上传失败: ${error.message}`);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleAnalyze() {
    if (!order) return;
    setAnalyzing(true);
    setPromptPreview("");
    try {
      const brief = await briefsApi.generate(order.id);
      setBriefs([brief, ...briefs]);
      await loadAll(order.id);
    } catch (error: any) {
      alert(`AI 分析失败: ${error.message}`);
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleConfirmBrief() {
    if (!order || !latestBrief) return;
    setSaving(true);
    try {
      await briefsApi.confirm(order.id, latestBrief.id, briefForm);
      await loadAll(order.id);
      alert("brief 已确认，后续样品图会使用这版结构化需求。");
    } catch (error: any) {
      alert(`确认失败: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handlePromptPreview() {
    if (!order || !latestBrief) return;
    try {
      const preview = await workflowApi.promptPreview({
        order_id: order.id,
        brief_id: latestBrief.id,
        provider: "openai",
        view_type: "main",
        quality_mode: "sample",
      });
      setPromptPreview(preview.provider_prompt);
    } catch (error: any) {
      alert(`预览失败: ${error.message}`);
    }
  }

  async function copyQuestions() {
    const text = questions.join("\n");
    if (!text) return;
    await navigator.clipboard.writeText(text);
    alert("追问问题已复制。");
  }

  if (loading) return <div className="loading">加载中...</div>;
  if (!order) return <div className="empty-state"><p>订单不存在</p></div>;

  const imageUrl = (filePath: string) =>
    `http://127.0.0.1:8765/api/file?path=${encodeURIComponent(filePath)}`;

  return (
    <div className="order-ai-workbench ck-workbench">
      <header className="studio-hero ck-hero">
        <button className="btn btn-outline btn-sm" onClick={() => navigate("/")}>
          返回订单
        </button>
        <div className="studio-title-group">
          <div className="studio-kicker">CuddleKine Intake Lab</div>
          <h2>{order.order_number} 需求识别与 brief</h2>
          <p>{order.source_summary || order.character_type || "等待素材识别"}</p>
        </div>
        <div className="studio-stats">
          <Metric label="素材" value={String(materials.length)} />
          <Metric label="brief 版本" value={latestBrief?.version ? String(latestBrief.version) : "-"} />
          <Metric label="状态" value={STATUS_LABELS[order.status] || order.status} />
        </div>
      </header>

      <div className="workbench-grid ck-studio-grid">
        <aside className="control-dock ck-left-panel">
          <section className="dock-section ck-panel">
            <div className="dock-title">上传素材</div>
            <div className="upload-stack">
              {MATERIAL_TYPES.map((materialType) => (
                <label key={materialType.value} className="btn btn-outline btn-sm">
                  {materialType.label}
                  <input
                    type="file"
                    accept="image/*,.txt"
                    hidden
                    disabled={uploading}
                    onChange={(event) => handleUpload(event, materialType.value)}
                  />
                </label>
              ))}
            </div>
            {uploading && <p className="dock-note">上传中...</p>}
          </section>

          <section className="dock-section ck-panel">
            <div className="dock-title">AI 流程</div>
            <button
              className="btn btn-primary"
              disabled={materials.length === 0 || analyzing}
              onClick={handleAnalyze}
            >
              {analyzing ? "识别中..." : "AI 识别客户需求"}
            </button>
            <div className={`model-status ${latestBrief?.is_confirmed ? "ok" : "bad"}`}>
              {latestBrief?.is_confirmed ? "brief 已确认" : "brief 待确认"}
            </div>
          </section>

          <section className="dock-section ck-panel">
            <div className="dock-title">素材列表</div>
            <div className="history-list">
              {materials.length ? materials.map((material) => (
                <button key={material.id} type="button">
                  <span>{material.original_name || material.type}</span>
                  <small>{material.processing_status || "pending"} / {material.detected_subject || material.type}</small>
                </button>
              )) : <p className="dock-empty">还没有素材</p>}
            </div>
          </section>
        </aside>

        <main className="sample-stage ck-stage">
          <div className="stage-toolbar ck-stage-toolbar">
            <div>
              <span className="stage-label">结构化需求</span>
              <h3>设计师确认 brief</h3>
              <p>AI 负责整理素材，最终由设计师确认哪些信息进入生成流程。</p>
            </div>
            <div className="stage-actions">
              <button className="btn btn-outline" disabled={!latestBrief} onClick={handlePromptPreview}>
                查看生成提示词
              </button>
              <button
                className="btn btn-primary"
                disabled={!latestBrief || saving}
                onClick={handleConfirmBrief}
              >
                {saving ? "确认中..." : "确认 brief"}
              </button>
              <button
                className="btn btn-outline"
                disabled={!order.confirmed_brief_id}
                onClick={() => navigate(`/orders/${order.id}/generate`)}
              >
                进入生成
              </button>
            </div>
          </div>

          {!latestBrief ? (
            <div className="empty-state">
              <p>上传客户参考图、聊天截图或文字素材后，点击 AI 识别客户需求。</p>
            </div>
          ) : (
            <section className="brief-editor">
              <div className="brief-form-grid">
                {BRIEF_FIELDS.map(([key, label]) => (
                  <div className="form-group" key={key}>
                    <label>{label}</label>
                    {key.includes("features") || key.includes("simplifications") || key.includes("changes") || key === "order_intent" ? (
                      <textarea
                        value={briefForm[key] || ""}
                        onChange={(event) => setBriefForm({ ...briefForm, [key]: event.target.value })}
                      />
                    ) : (
                      <input
                        value={briefForm[key] || ""}
                        onChange={(event) => setBriefForm({ ...briefForm, [key]: event.target.value })}
                      />
                    )}
                  </div>
                ))}
              </div>

              {missingItems.length > 0 && (
                <div className="notice-panel warning">
                  <strong>待确认字段</strong>
                  {missingItems.map((item) => (
                    <span key={item.field}>{item.description}: {item.reason || item.field}</span>
                  ))}
                </div>
              )}

              {promptPreview && (
                <details className="prompt-preview" open>
                  <summary>Prompt Preview</summary>
                  <textarea readOnly value={promptPreview} />
                </details>
              )}
            </section>
          )}
        </main>

        <aside className="version-dock ck-right-panel">
          <section className="dock-section ck-panel">
            <div className="dock-title">客户追问</div>
            {questions.length ? (
              <>
                <div className="question-list">
                  {questions.map((question) => <p key={question}>{question}</p>)}
                </div>
                <button className="btn btn-outline btn-sm" onClick={copyQuestions}>
                  复制追问
                </button>
              </>
            ) : (
              <p className="dock-empty">暂无追问</p>
            )}
          </section>

          <section className="dock-section ck-panel">
            <div className="dock-title">风险与工艺</div>
            {risks.length ? (
              <div className="question-list">
                {risks.map((risk) => <p key={risk}>{risk}</p>)}
              </div>
            ) : (
              <p className="dock-success">未发现明显风险</p>
            )}
          </section>

          <section className="dock-section ck-panel">
            <div className="dock-title">素材预览</div>
            <div className="material-grid compact">
              {materials.map((material) => (
                <div key={material.id} className="material-item">
                  {material.file_path?.match(/\.(png|jpg|jpeg|gif|webp)$/i) ? (
                    <img src={imageUrl(material.file_path)} alt={material.original_name || ""} />
                  ) : (
                    <div className="sample-placeholder small"><strong>TEXT</strong></div>
                  )}
                  <span className="tag">{material.type}</span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function safeJson<T>(value: string, fallback: T): T {
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join("\n");
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}
