import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { generationApi, providersApi, settingsApi, exportApi, ordersApi, type Generation, type Order, type ProviderInfo } from "../api/client";

type Tab = "main" | "modify" | "multiview" | "export";

const QUALITY_OPTIONS = [
  { value: "draft", label: "草稿", hint: "快速探索" },
  { value: "sample", label: "样品图", hint: "客户预览" },
  { value: "final", label: "最终确认", hint: "交付确认" },
];

const STEPS: { key: Tab; label: string; short: string }[] = [
  { key: "main", label: "主视图候选", short: "主图" },
  { key: "modify", label: "局部修改", short: "修改" },
  { key: "multiview", label: "多视图", short: "三视图" },
  { key: "export", label: "导出确认板", short: "导出" },
];

export default function GenerationPanel() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const id = Number(orderId);

  const [order, setOrder] = useState<Order | null>(null);
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("main");
  const [generating, setGenerating] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [modifyText, setModifyText] = useState("");
  const [lockedRegions, setLockedRegions] = useState("");
  const [boardPath, setBoardPath] = useState("");
  const [packagePath, setPackagePath] = useState("");
  const [loading, setLoading] = useState(true);
  const [selProvider, setSelProvider] = useState("comfyui");
  const [selModel, setSelModel] = useState("");
  const [selQuality, setSelQuality] = useState("sample");

  useEffect(() => {
    loadAll();
    providersApi.list().then(setProviders).catch(() => {});
    settingsApi.get()
      .then((settings) => {
        setSelProvider(settings.default_provider || "comfyui");
        setSelModel(settings.default_model || "");
        setSelQuality(settings.default_quality || "sample");
      })
      .catch(() => {});
  }, [orderId]);

  const loadAll = async () => {
    try {
      const [o, gens] = await Promise.all([ordersApi.get(id), generationApi.list(id)]);
      setOrder(o);
      setGenerations(gens);
      if (o.confirmed_version_id) setSelectedId(o.confirmed_version_id);
    } catch (e: any) {
      alert(`加载失败: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const curProvider = providers.find((p) => p.id === selProvider);
  const curModels = curProvider?.models || [];

  const handleGenerate = async (viewType: string, derivationType: string) => {
    setGenerating(true);
    try {
      const gen = await generationApi.generate({
        order_id: id,
        provider: selProvider,
        model: selModel || undefined,
        quality_mode: selQuality,
        view_type: viewType,
        derivation_type: derivationType,
        source_version_id: selectedId || undefined,
        locked_regions: lockedRegions || undefined,
        modification_prompt: derivationType === "local_modify" ? modifyText.trim() : undefined,
        transparent_background: true,
      });
      setGenerations([gen, ...generations]);
      if (viewType === "main" && !selectedId && gen.file_path) setSelectedId(gen.id);
    } catch (e: any) {
      alert(`生成失败: ${e.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleConfirm = async (genId: number) => {
    try {
      await generationApi.confirm(genId);
      setSelectedId(genId);
      await loadAll();
    } catch (e: any) {
      alert(`确认失败: ${e.message}`);
    }
  };

  const handleBatchMultiview = async () => {
    if (!selectedId) return;
    setGenerating(true);
    try {
      const results = await generationApi.batchMultiview({
        order_id: id,
        source_version_id: selectedId,
        provider: selProvider,
        model: selModel || undefined,
        quality_mode: selQuality,
        transparent_background: true,
      });
      setGenerations([...results, ...generations]);
    } catch (e: any) {
      alert(`生成失败: ${e.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    try {
      const result = await exportApi.board(id);
      setBoardPath(result.board_path);
      setActiveTab("export");
    } catch (e: any) {
      alert(`导出失败: ${e.message}`);
    }
  };

  const handlePackage = async () => {
    try {
      const result = await exportApi.package(id);
      setPackagePath(result.package_path);
    } catch (e: any) {
      alert(`导出资料包失败: ${e.message}`);
    }
  };

  const mainCandidates = generations.filter((g) => g.view_type === "main");
  const frontViews = generations.filter((g) => g.view_type === "front");
  const sideViews = generations.filter((g) => g.view_type === "side");
  const backViews = generations.filter((g) => g.view_type === "back");
  const latestFront = frontViews[0];
  const latestSide = sideViews[0];
  const latestBack = backViews[0];
  const hasAllViews = Boolean(latestFront && latestSide && latestBack);
  const selectedGeneration = generations.find((g) => g.id === selectedId) || mainCandidates[0] || null;
  const selectedQuality = QUALITY_OPTIONS.find((q) => q.value === selQuality);

  if (loading) return <div className="loading">加载中</div>;
  if (!order) return <div className="empty-state"><p>订单不存在</p></div>;

  const imageUrl = (filePath: string) =>
    `http://127.0.0.1:8765/api/file?path=${encodeURIComponent(filePath)}`;

  const generationStatus = selectedGeneration?.error_message
    ? "生成失败"
    : selectedGeneration?.file_path
      ? "可确认"
      : "待生成";

  return (
    <div className="sampling-workbench">
      <header className="studio-hero">
        <button className="btn btn-outline btn-sm" onClick={() => navigate(`/orders/${id}`)}>
          返回订单
        </button>
        <div className="studio-title-group">
          <div className="studio-kicker">CuddleKine Sample Lab</div>
          <h2>{order.order_number} 生成工作台</h2>
          <p>{order.character_type || "未填写角色类型"} · {order.colors || "未填写色彩"} · {order.target_height ? `${order.target_height}cm` : "尺寸待定"}</p>
        </div>
        <div className="studio-stats">
          <div><strong>{mainCandidates.length}</strong><span>主图版本</span></div>
          <div><strong>{hasAllViews ? "3/3" : `${[latestFront, latestSide, latestBack].filter(Boolean).length}/3`}</strong><span>三视图</span></div>
          <div><strong>{generationStatus}</strong><span>当前状态</span></div>
        </div>
      </header>

      <div className="workbench-grid">
        <aside className="control-dock">
          <div className="dock-section">
            <div className="dock-title">工作流</div>
            <div className="step-rail">
              {STEPS.map((step, index) => (
                <button
                  key={step.key}
                  className={`step-item ${activeTab === step.key ? "active" : ""}`}
                  onClick={() => setActiveTab(step.key)}
                >
                  <span>{index + 1}</span>
                  <strong>{step.short}</strong>
                  <small>{step.label}</small>
                </button>
              ))}
            </div>
          </div>

          <div className="dock-section">
            <div className="dock-title">模型控制</div>
            <div className="form-group">
              <label>生成服务</label>
              <select value={selProvider} onChange={(e) => { setSelProvider(e.target.value); setSelModel(""); }}>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}{!p.configured ? "（未配置）" : ""}</option>
                ))}
              </select>
            </div>
            {curModels.length > 0 && (
              <div className="form-group">
                <label>模型</label>
                <select value={selModel} onChange={(e) => setSelModel(e.target.value)}>
                  <option value="">默认模型</option>
                  {curModels.map((m) => (
                    <option key={m.id} value={m.id}>{m.name} · {m.best_for}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="quality-segments">
              {QUALITY_OPTIONS.map((q) => (
                <button
                  key={q.value}
                  className={selQuality === q.value ? "active" : ""}
                  onClick={() => setSelQuality(q.value)}
                >
                  <strong>{q.label}</strong>
                  <span>{q.hint}</span>
                </button>
              ))}
            </div>
            <div className={`model-status ${curProvider?.configured ? "ok" : "bad"}`}>
              {curProvider?.configured ? "已连接" : "未配置"}
            </div>
          </div>

          {activeTab === "modify" && (
            <div className="dock-section">
              <div className="dock-title">局部修改</div>
              <div className="form-group">
                <label>修改描述</label>
                <textarea
                  value={modifyText}
                  onChange={(e) => setModifyText(e.target.value)}
                  placeholder="例如：把耳朵变大 20%，眼睛改成蓝色"
                />
              </div>
              <div className="form-group">
                <label>锁定区域</label>
                <input
                  value={lockedRegions}
                  onChange={(e) => setLockedRegions(e.target.value)}
                  placeholder="如：头部,身体轮廓"
                />
              </div>
            </div>
          )}

          <div className="dock-section">
            <div className="dock-title">订单要点</div>
            <dl className="brief-list">
              <div><dt>角色</dt><dd>{order.character_type || "-"}</dd></div>
              <div><dt>关键特征</dt><dd>{order.key_features || "-"}</dd></div>
              <div><dt>材质</dt><dd>{order.material_preference || "短毛绒 / 刺绣 / 填充棉"}</dd></div>
              <div><dt>配件</dt><dd>{order.accessories || "-"}</dd></div>
            </dl>
          </div>
        </aside>

        <main className="sample-stage">
          <div className="stage-toolbar">
            <div>
              <span className="stage-label">{STEPS.find((s) => s.key === activeTab)?.label}</span>
              <h3>{activeTab === "main" ? "主样品候选" : activeTab === "modify" ? "定向修版" : activeTab === "multiview" ? "结构三视图" : "客户确认输出"}</h3>
            </div>
            <div className="stage-actions">
              {activeTab === "main" && (
                <button className="btn btn-primary" onClick={() => handleGenerate("main", "main_view_candidate")} disabled={generating}>
                  {generating ? "生成中" : "生成主视图"}
                </button>
              )}
              {activeTab === "modify" && (
                <button className="btn btn-primary" onClick={() => handleGenerate("main", "local_modify")} disabled={generating || !selectedId || !modifyText.trim()}>
                  {generating ? "生成中" : "应用修改"}
                </button>
              )}
              {activeTab === "multiview" && (
                <button className="btn btn-primary" onClick={handleBatchMultiview} disabled={generating || !selectedId}>
                  {generating ? "生成中" : "生成三视图"}
                </button>
              )}
              {activeTab === "export" && (
                <>
                  <button className="btn btn-primary" onClick={handleExport}>生成确认板</button>
                  <button className="btn btn-outline" onClick={handlePackage}>导出 ZIP</button>
                </>
              )}
            </div>
          </div>

          {generating && <div className="studio-progress">正在生成样品图，通常需要 1-3 分钟</div>}

          {activeTab !== "export" && (
            <section className="hero-sample-card">
              {selectedGeneration?.file_path ? (
                <img src={imageUrl(selectedGeneration.file_path)} alt="当前样品图" />
              ) : (
                <div className="sample-placeholder">
                  <strong>等待生成样品</strong>
                  <span>上传参考图并填写订单信息后，从左侧选择模型开始生成。</span>
                </div>
              )}
              <div className="sample-caption">
                <span>{selectedGeneration ? `Version #${selectedGeneration.id}` : "No version"}</span>
                <span>{selectedGeneration?.provider || selProvider} / {selectedGeneration?.provider_model || selectedQuality?.label || "-"}</span>
                <span>{selectedGeneration?.duration ? `${selectedGeneration.duration}s` : "透明背景优先"}</span>
              </div>
            </section>
          )}

          {activeTab === "main" && (
            <VersionGrid
              generations={mainCandidates}
              selectedId={selectedId}
              imageUrl={imageUrl}
              onSelect={setSelectedId}
              onConfirm={handleConfirm}
            />
          )}

          {activeTab === "modify" && (
            <VersionGrid
              generations={mainCandidates}
              selectedId={selectedId}
              imageUrl={imageUrl}
              onSelect={setSelectedId}
              onConfirm={handleConfirm}
              compactTitle="修版轨道"
            />
          )}

          {activeTab === "multiview" && (
            <div className="multiview-stage">
              <ViewSlot label="正面 Front" generation={latestFront} imageUrl={imageUrl} />
              <ViewSlot label="侧面 Side" generation={latestSide} imageUrl={imageUrl} />
              <ViewSlot label="背面 Back" generation={latestBack} imageUrl={imageUrl} />
            </div>
          )}

          {activeTab === "export" && (
            <div className="export-stage">
              {boardPath ? (
                <img src={imageUrl(boardPath)} alt="确认板" />
              ) : (
                <div className="sample-placeholder">
                  <strong>{hasAllViews ? "可以生成确认板" : "三视图还不完整"}</strong>
                  <span>{hasAllViews ? "确认板会整合主图、正面、侧面、背面和订单信息。" : "请先生成正面、侧面和背面视图，再导出确认板。"}</span>
                </div>
              )}
              {packagePath && <div className="export-path">资料包已导出：{packagePath}</div>}
            </div>
          )}
        </main>

        <aside className="version-dock">
          <div className="dock-section">
            <div className="dock-title">当前版本</div>
            {selectedGeneration ? (
              <div className="version-inspector">
                <strong>#{selectedGeneration.id}</strong>
                <span>{selectedGeneration.provider}/{selectedGeneration.provider_model || selectedGeneration.model_name || "-"}</span>
                <span>{selectedGeneration.quality_mode || "-"}</span>
                <span>{selectedGeneration.error_message ? "失败" : selectedGeneration.file_path ? "成功" : "无输出"}</span>
                {selectedGeneration.file_path && (
                  <button className="btn btn-primary btn-sm" onClick={() => handleConfirm(selectedGeneration.id)}>
                    确认版本
                  </button>
                )}
              </div>
            ) : (
              <p className="dock-empty">还没有主图版本</p>
            )}
          </div>

          <div className="dock-section">
            <div className="dock-title">三视图检查</div>
            <div className="view-check-list">
              <span className={latestFront ? "done" : ""}>正面</span>
              <span className={latestSide ? "done" : ""}>侧面</span>
              <span className={latestBack ? "done" : ""}>背面</span>
            </div>
            <p className={hasAllViews ? "dock-success" : "dock-note"}>
              {hasAllViews ? "三视图齐全，可以导出确认板。" : "请先补齐正/侧/背三视图。"}
            </p>
          </div>

          <details className="history-dock" open>
            <summary>版本历史 ({generations.length})</summary>
            <div className="history-list">
              {generations.map((g) => (
                <button
                  key={g.id}
                  className={g.id === selectedId ? "active" : ""}
                  onClick={() => g.file_path && setSelectedId(g.id)}
                >
                  <span>#{g.id} {g.view_type}</span>
                  <small>{g.provider}/{g.provider_model || g.model_name || "-"}</small>
                </button>
              ))}
            </div>
          </details>
        </aside>
      </div>
    </div>
  );
}

function VersionGrid({
  generations,
  selectedId,
  imageUrl,
  onSelect,
  onConfirm,
  compactTitle = "候选版本",
}: {
  generations: Generation[];
  selectedId: number | null;
  imageUrl: (filePath: string) => string;
  onSelect: (id: number) => void;
  onConfirm: (id: number) => void;
  compactTitle?: string;
}) {
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
        {generations.map((gen) => (
          <div
            key={gen.id}
            className={`image-card ${selectedId === gen.id ? "selected" : ""}`}
            onClick={() => gen.file_path && onSelect(gen.id)}
          >
            {gen.file_path ? (
              <img src={imageUrl(gen.file_path)} alt={`候选 ${gen.id}`} />
            ) : (
              <div className="sample-placeholder small">
                <strong>无输出</strong>
                <span>{gen.error_message || "等待结果"}</span>
              </div>
            )}
            <div className="info">
              <span>{gen.provider}/{gen.provider_model || "-"}</span>
              <span>{gen.duration ? `${gen.duration}s` : "-"}</span>
              {gen.file_path && (
                <button className="btn btn-outline btn-sm" onClick={(e) => { e.stopPropagation(); onConfirm(gen.id); }}>
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

function ViewSlot({
  label,
  generation,
  imageUrl,
}: {
  label: string;
  generation?: Generation;
  imageUrl: (filePath: string) => string;
}) {
  return (
    <div className={`view-slot ${generation?.file_path ? "has-image" : ""}`}>
      <div className="view-label">{label}</div>
      {generation?.file_path ? (
        <img src={imageUrl(generation.file_path)} alt={label} />
      ) : (
        <span>待生成</span>
      )}
    </div>
  );
}
