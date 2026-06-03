import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ordersApi, materialsApi, briefsApi,
  type Order, type Material, type Brief,
} from "../api/client";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿", material_imported: "素材已导入",
  brief_pending: "待确认", brief_confirmed: "已确认",
  generating: "生成中", reviewing: "审核中",
  exported: "已导出", archived: "已归档",
};

const MATERIAL_TYPES = [
  { value: "text", label: "文字描述" },
  { value: "chat_screenshot", label: "聊天截图" },
  { value: "photo", label: "照片" },
  { value: "sketch", label: "手绘" },
  { value: "reference", label: "参考玩具图" },
];

export default function OrderDetail() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const isNew = !orderId;

  const [order, setOrder] = useState<Order | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [briefs, setBriefs] = useState<Brief[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);

  // 编辑表单
  const [form, setForm] = useState<Partial<Order>>({});

  useEffect(() => {
    if (orderId) loadOrder(Number(orderId));
  }, [orderId]);

  const loadOrder = async (id: number) => {
    setLoading(true);
    try {
      const o = await ordersApi.get(id);
      setOrder(o);
      setForm({
        customer_name: o.customer_name || "",
        character_type: o.character_type || "",
        target_height: o.target_height || undefined,
        main_proportions: o.main_proportions || "",
        colors: o.colors || "",
        material_preference: o.material_preference || "",
        accessories: o.accessories || "",
        key_features: o.key_features || "",
        allowed_simplifications: o.allowed_simplifications || "",
        pending_items: o.pending_items || "",
        craft_notes: o.craft_notes || "",
      });
      await Promise.all([loadMaterials(id), loadBriefs(id)]);
    } catch (e: any) {
      alert(`加载失败: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadMaterials = async (id: number) => {
    try { setMaterials(await materialsApi.list(id)); } catch {}
  };
  const loadBriefs = async (id: number) => {
    try { setBriefs(await briefsApi.list(id)); } catch {}
  };

  const handleSave = async () => {
    if (!order) return;
    try {
      const updated = await ordersApi.update(order.id, form);
      setOrder(updated);
      alert("已保存");
    } catch (e: any) {
      alert(`保存失败: ${e.message}`);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: string) => {
    if (!order || !e.target.files?.length) return;
    setUploading(true);
    try {
      await materialsApi.upload(order.id, e.target.files[0], type);
      await loadMaterials(order.id);
    } catch (err: any) {
      alert(`上传失败: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!order) return;
    setAnalyzing(true);
    try {
      const brief = await briefsApi.analyze(order.id);
      setBriefs([brief, ...briefs]);
      await loadOrder(order.id);
    } catch (e: any) {
      alert(`分析失败: ${e.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReply = async (briefId: number) => {
    // 将缺失信息作为追问，弹出表单让用户补充
    const brief = briefs.find((b) => b.id === briefId);
    if (!brief?.missing_info) return;
    const missingItems: { field: string; description: string }[] = JSON.parse(brief.missing_info);

    const replies: Record<string, string> = {};
    for (const item of missingItems) {
      const val = prompt(`${item.description} (${item.field}):`) || "";
      if (val) replies[item.field] = val;
    }
    if (!Object.keys(replies).length) return;

    try {
      await briefsApi.reply(briefId, replies);
      await loadBriefs(order!.id);
      await loadOrder(order!.id);
    } catch (e: any) {
      alert(`提交失败: ${e.message}`);
    }
  };

  const latestBrief = briefs[0];
  const missingItems: { field: string; description: string }[] = latestBrief?.missing_info
    ? JSON.parse(latestBrief.missing_info) : [];
  const structured: Record<string, string> = latestBrief?.structured_content
    ? JSON.parse(latestBrief.structured_content) : {};

  if (loading) return <div className="loading">加载中</div>;

  return (
    <div>
      {/* 顶部导航 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20 }}>
            {order ? `订单 ${order.order_number}` : "新建订单"}
          </h2>
          {order && (
            <span className={`status-badge status-${order.status}`} style={{ marginLeft: 8, verticalAlign: "middle" }}>
              {STATUS_LABELS[order.status] || order.status}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {order && (
            <>
              <button className="btn btn-outline btn-sm" onClick={handleSave}>保存</button>
              <button
                className="btn btn-primary"
                onClick={() => navigate(`/orders/${order.id}/generate`)}
              >
                进入生成
              </button>
            </>
          )}
        </div>
      </div>

      {/* 基本信息 */}
      <div className="card">
        <div className="card-header">基本信息</div>
        <div className="form-row">
          <div className="form-group">
            <label>客户名称</label>
            <input value={form.customer_name || ""} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} />
          </div>
          <div className="form-group">
            <label>角色类型</label>
            <input value={form.character_type || ""} onChange={(e) => setForm({ ...form, character_type: e.target.value })} />
          </div>
        </div>
      </div>

      {/* 需求详情 */}
      <div className="card">
        <div className="card-header">需求详情</div>
        <div className="form-row">
          <div className="form-group">
            <label>目标成品高度 (cm)</label>
            <input type="number" value={form.target_height || ""} onChange={(e) => setForm({ ...form, target_height: Number(e.target.value) })} />
          </div>
          <div className="form-group">
            <label>颜色</label>
            <input value={form.colors || ""} onChange={(e) => setForm({ ...form, colors: e.target.value })} />
          </div>
        </div>
        <div className="form-group">
          <label>主要比例</label>
          <input value={form.main_proportions || ""} onChange={(e) => setForm({ ...form, main_proportions: e.target.value })} />
        </div>
        <div className="form-group">
          <label>材质倾向</label>
          <input value={form.material_preference || ""} onChange={(e) => setForm({ ...form, material_preference: e.target.value })} />
        </div>
        <div className="form-group">
          <label>配件</label>
          <input value={form.accessories || ""} onChange={(e) => setForm({ ...form, accessories: e.target.value })} />
        </div>
        <div className="form-group">
          <label>关键辨识特征</label>
          <textarea value={form.key_features || ""} onChange={(e) => setForm({ ...form, key_features: e.target.value })} />
        </div>
        <div className="form-group">
          <label>允许简化项</label>
          <input value={form.allowed_simplifications || ""} onChange={(e) => setForm({ ...form, allowed_simplifications: e.target.value })} />
        </div>
        <div className="form-group">
          <label>工艺备注</label>
          <textarea value={form.craft_notes || ""} onChange={(e) => setForm({ ...form, craft_notes: e.target.value })} />
        </div>
      </div>

      {/* 素材管理 */}
      {order && (
        <div className="card">
          <div className="card-header">
            素材 ({materials.length})
            <div style={{ display: "flex", gap: 6 }}>
              {MATERIAL_TYPES.map((mt) => (
                <label key={mt.value} className="btn btn-outline btn-sm" style={{ cursor: "pointer", position: "relative" }}>
                  {mt.label}
                  <input
                    type="file"
                    accept="image/*,.txt"
                    style={{ display: "none" }}
                    onChange={(e) => handleUpload(e, mt.value)}
                    disabled={uploading}
                  />
                </label>
              ))}
            </div>
          </div>

          {uploading && <div className="loading">上传中</div>}

          {materials.length === 0 ? (
            <div className="empty-state">
              <p>暂无素材，点击上方按钮上传</p>
            </div>
          ) : (
            <div className="material-grid">
              {materials.map((m) => (
                <div key={m.id} className="material-item">
                  {m.file_path?.match(/\.(png|jpg|jpeg|gif|webp)$/i) ? (
                    <img src={`http://127.0.0.1:8765/api/file?path=${encodeURIComponent(m.file_path!)}`} alt={m.original_name || ""} />
                  ) : (
                    <div style={{ height: 120, background: "#f0f0f5", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>
                      📄
                    </div>
                  )}
                  <span className="tag">{MATERIAL_TYPES.find((t) => t.value === m.type)?.label || m.type}</span>
                  <div className="caption">{m.original_name || m.type}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Brief 分析 */}
      {order && (
        <div className="card">
          <div className="card-header">
            Brief 需求整理
            <div style={{ display: "flex", gap: 8 }}>
              {materials.length > 0 && (
                <button className="btn btn-primary btn-sm" onClick={handleAnalyze} disabled={analyzing}>
                  {analyzing ? "分析中" : "分析素材"}
                </button>
              )}
            </div>
          </div>

          {latestBrief ? (
            <div>
              {/* 已提取 */}
              <div style={{ marginBottom: 12 }}>
                <strong style={{ fontSize: 13, color: "#2e7d32" }}>已提取字段：</strong>
                <div style={{ marginTop: 4 }}>
                  {Object.keys(structured).length === 0 ? (
                    <span style={{ color: "#999" }}>未提取到结构化信息</span>
                  ) : (
                    <table className="table" style={{ fontSize: 12 }}>
                      <tbody>
                        {Object.entries(structured).map(([key, val]) => (
                          <tr key={key}>
                            <td style={{ fontWeight: 600, width: 140 }}>{key}</td>
                            <td>{String(val)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* 缺失 */}
              {missingItems.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ fontSize: 13, color: "#e65100" }}>
                    缺失信息 ({missingItems.length} 项）：
                  </strong>
                  <ul style={{ margin: "4px 0 0 20px", fontSize: 12, color: "#666" }}>
                    {missingItems.map((item) => (
                      <li key={item.field}>
                        {item.description} — {item.field}
                      </li>
                    ))}
                  </ul>
                  {!latestBrief.is_confirmed && (
                    <button
                      className="btn btn-outline btn-sm"
                      style={{ marginTop: 8 }}
                      onClick={() => handleReply(latestBrief.id)}
                    >
                      补充缺失信息
                    </button>
                  )}
                </div>
              )}

              {/* 状态 */}
              <div style={{ fontSize: 12, color: latestBrief.is_confirmed ? "#2e7d32" : "#e65100" }}>
                {latestBrief.is_confirmed ? "Brief 已确认" : "待确认 — 请补充缺失信息"}
                <span style={{ marginLeft: 8, color: "#999" }}>版本 {latestBrief.version}</span>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>{materials.length === 0 ? "请先导入素材" : "素材已就绪，点击「分析素材」生成 brief"}</p>
            </div>
          )}

          {/* 历史版本 */}
          {briefs.length > 1 && (
            <details style={{ marginTop: 16, fontSize: 12, color: "#999" }}>
              <summary>历史版本 ({briefs.length - 1})</summary>
              {briefs.slice(1).map((b) => (
                <div key={b.id} style={{ marginTop: 4 }}>
                  v{b.version} — {b.created_at?.slice(0, 19)} — {b.is_confirmed ? "已确认" : "未确认"}
                </div>
              ))}
            </details>
          )}
        </div>
      )}
    </div>
  );
}
