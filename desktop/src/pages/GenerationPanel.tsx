import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  exportApi,
  generationApi,
  ordersApi,
  providersApi,
  settingsApi,
  type Generation,
  type Order,
  type ProviderInfo,
} from "../api/client";

type Tab = "main" | "modify" | "multiview" | "export";

const QUALITY_OPTIONS = [
  { value: "draft", label: "草稿", hint: "低成本探索" },
  { value: "sample", label: "样品", hint: "客户预览" },
  { value: "final", label: "定稿", hint: "交付确认" },
];

const STEPS: { key: Tab; label: string; short: string; note: string }[] = [
  { key: "main", label: "主图候选", short: "主图", note: "确定样品的第一视觉" },
  { key: "modify", label: "主图修版", short: "修版", note: "基于已选主图做定向调整" },
  { key: "multiview", label: "结构三视图", short: "三视图", note: "正面、侧面、背面一致输出" },
  { key: "export", label: "交付资料", short: "导出", note: "客户图与工厂资料分离" },
];

const VIEW_LABELS: Record<string, string> = {
  main: "主图",
  front: "正面",
  side: "侧面",
  back: "背面",
};

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
  const [designerPrompt, setDesignerPrompt] = useState("");
  const [lockedRegions, setLockedRegions] = useState("");
  const [boardPath, setBoardPath] = useState("");
  const [factoryPdfPath, setFactoryPdfPath] = useState("");
  const [packagePath, setPackagePath] = useState("");
  const [maskEditor, setMaskEditor] = useState<Generation | null>(null);
  const [loading, setLoading] = useState(true);
  const [selProvider, setSelProvider] = useState("openai");
  const [selModel, setSelModel] = useState("");
  const [selQuality, setSelQuality] = useState("sample");

  useEffect(() => {
    loadAll();
    Promise.all([providersApi.list(), settingsApi.get()])
      .then(([nextProviders, settings]) => {
        setProviders(nextProviders);
        const openaiReady = nextProviders.some((provider) => provider.id === "openai" && provider.configured);
        const preferredProvider = openaiReady && (!settings.default_provider || settings.default_provider === "comfyui")
          ? "openai"
          : settings.default_provider || "openai";
        setSelProvider(preferredProvider);
        setSelModel(preferredProvider === "openai" ? settings.default_model || "gpt-image-1.5" : settings.default_model || "");
        setSelQuality(openaiReady ? settings.default_quality || "final" : settings.default_quality || "sample");
      })
      .catch(() => {});
  }, [orderId]);

  async function loadAll() {
    try {
      const [loadedOrder, gens] = await Promise.all([
        ordersApi.get(id),
        generationApi.list(id),
      ]);
      setOrder(loadedOrder);
      setGenerations(gens);
      if (loadedOrder.confirmed_version_id) {
        setSelectedId(loadedOrder.confirmed_version_id);
      }
    } catch (error: any) {
      alert(`加载失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  const curProvider = providers.find((provider) => provider.id === selProvider);
  const curModels = curProvider?.models || [];
  const mainCandidates = generations.filter((generation) => generation.view_type === "main");
  const frontViews = generations.filter((generation) => generation.view_type === "front");
  const sideViews = generations.filter((generation) => generation.view_type === "side");
  const backViews = generations.filter((generation) => generation.view_type === "back");
  const latestFront = frontViews[0];
  const latestSide = sideViews[0];
  const latestBack = backViews[0];
  const hasAllViews = Boolean(latestFront && latestSide && latestBack);
  const selectedGeneration = generations.find((generation) => generation.id === selectedId) || mainCandidates[0] || null;
  const selectedQuality = QUALITY_OPTIONS.find((quality) => quality.value === selQuality);
  const confirmedMainId = order?.confirmed_version_id || null;
  const selectedIsConfirmedMain = Boolean(selectedId && confirmedMainId === selectedId);
  const activeStep = STEPS.find((step) => step.key === activeTab) || STEPS[0];
  const providerQualityNote = providerNote(selProvider);

  async function handleGenerate(viewType: string, derivationType: string) {
    if (selQuality !== "draft" && !order?.confirmed_brief_id) {
      alert("请先在订单详情页确认 structured brief，再生成样品图。");
      return;
    }
    setGenerating(true);
    try {
      const gen = await generationApi.generate({
        order_id: id,
        provider: selProvider,
        model: selModel || undefined,
        quality_mode: selQuality,
        brief_id: order?.confirmed_brief_id || undefined,
        view_type: viewType,
        derivation_type: derivationType,
        source_version_id: selectedId || undefined,
        locked_regions: lockedRegions || undefined,
        modification_prompt: derivationType === "local_modify" ? modifyText.trim() : designerPrompt.trim() || undefined,
        transparent_background: selProvider === "comfyui",
      });
      setGenerations([gen, ...generations]);
      if (viewType === "main" && !selectedId && gen.file_path) {
        setSelectedId(gen.id);
      }
    } catch (error: any) {
      alert(`生成失败: ${error.message}`);
    } finally {
      setGenerating(false);
    }
  }

  async function handleConfirm(genId: number) {
    try {
      await generationApi.confirm(genId);
      setSelectedId(genId);
      await loadAll();
    } catch (error: any) {
      alert(`确认失败: ${error.message}`);
    }
  }

  async function handleBatchMultiview() {
    if (!selectedId) return;
    if (!selectedIsConfirmedMain) {
      alert("请先确认一个主图版本，再生成三视图。三视图会引用已确认主图。");
      return;
    }
    if (selQuality !== "draft" && !order?.confirmed_brief_id) {
      alert("请先确认 structured brief，再生成三视图。");
      return;
    }
    setGenerating(true);
    try {
      const results = await generationApi.batchMultiview({
        order_id: id,
        source_version_id: selectedId,
        provider: selProvider,
        model: selModel || undefined,
        quality_mode: selQuality,
        brief_id: order?.confirmed_brief_id || undefined,
        modification_prompt: designerPrompt.trim() || undefined,
        transparent_background: selProvider === "comfyui",
      });
      setGenerations([...results, ...generations]);
    } catch (error: any) {
      alert(`生成失败: ${error.message}`);
    } finally {
      setGenerating(false);
    }
  }

  async function handleExport() {
    try {
      const result = await exportApi.board(id);
      setBoardPath(result.board_path);
      setActiveTab("export");
    } catch (error: any) {
      alert(`导出失败: ${error.message}`);
    }
  }

  async function handleFactoryPdf() {
    try {
      const result = await exportApi.factoryPdf(id);
      setFactoryPdfPath(result.factory_pdf_path);
      setActiveTab("export");
    } catch (error: any) {
      alert(`导出工厂 PDF 失败: ${error.message}`);
    }
  }

  async function handlePackage() {
    try {
      const result = await exportApi.package(id);
      setPackagePath(result.package_path);
      setFactoryPdfPath(result.factory_pdf_path);
      setActiveTab("export");
    } catch (error: any) {
      alert(`导出资料包失败: ${error.message}`);
    }
  }

  async function handleMaskedRevision(generation: Generation, maskDataUrl: string, prompt: string) {
    if (!generation.file_path) return;
    if (!prompt.trim()) {
      alert("请填写这次局部修改要调整什么。");
      return;
    }
    setGenerating(true);
    try {
      const gen = await generationApi.generate({
        order_id: id,
        provider: selProvider,
        model: selModel || undefined,
        quality_mode: selQuality,
        brief_id: order?.confirmed_brief_id || undefined,
        view_type: generation.view_type,
        derivation_type: "local_modify",
        source_version_id: generation.id,
        modification_prompt: prompt.trim(),
        locked_regions: "Painted mask revision. Only the brushed mask area may change.",
        transparent_background: selProvider === "comfyui",
        overrides: { mask_data_url: maskDataUrl },
      });
      setGenerations([gen, ...generations]);
      setMaskEditor(null);
    } catch (error: any) {
      alert(`局部修版失败: ${error.message}`);
    } finally {
      setGenerating(false);
    }
  }

  if (loading) return <div className="loading">加载中...</div>;
  if (!order) return <div className="empty-state"><p>订单不存在</p></div>;

  const imageUrl = (filePath: string) =>
    `http://127.0.0.1:8765/api/file?path=${encodeURIComponent(filePath)}`;

  const generationStatus = selectedGeneration?.error_message
    ? "生成失败"
    : selectedGeneration?.file_path
      ? "可确认"
      : "待生成";

  return (
    <div className="sampling-workbench ck-workbench">
      <header className="studio-hero ck-hero">
        <button className="btn btn-outline btn-sm" onClick={() => navigate(`/orders/${id}`)}>
          返回订单
        </button>
        <div className="studio-title-group">
          <div className="studio-kicker">CuddleKine Atelier</div>
          <h2>{order.order_number} 样品工作台</h2>
          <p>
            {order.character_type || "角色未填写"} / {order.colors || "颜色未填写"} / {order.target_height ? `${order.target_height}cm` : "尺寸待定"}
          </p>
        </div>
        <div className="studio-stats">
          <Metric label="主图版本" value={String(mainCandidates.length)} />
          <Metric label="三视图" value={hasAllViews ? "3/3" : `${[latestFront, latestSide, latestBack].filter(Boolean).length}/3`} />
          <Metric label="当前状态" value={generationStatus} />
        </div>
      </header>

      <div className="workbench-grid ck-studio-grid">
        <aside className="control-dock ck-left-panel">
          <section className="dock-section ck-panel">
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
                  <small>{step.note}</small>
                </button>
              ))}
            </div>
          </section>

          <section className="dock-section ck-panel">
            <div className="dock-title">模型与质量</div>
            <div className="form-group">
              <label>生成服务</label>
              <select value={selProvider} onChange={(event) => { setSelProvider(event.target.value); setSelModel(""); }}>
                {providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}{!provider.configured ? "（未配置）" : ""}
                  </option>
                ))}
              </select>
            </div>
            {curModels.length > 0 && (
              <div className="form-group">
                <label>模型</label>
                <select value={selModel} onChange={(event) => setSelModel(event.target.value)}>
                  <option value="">默认模型</option>
                  {curModels.map((model) => (
                    <option key={model.id} value={model.id}>{model.name} / {model.best_for}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="quality-segments">
              {QUALITY_OPTIONS.map((quality) => (
                <button
                  key={quality.value}
                  className={selQuality === quality.value ? "active" : ""}
                  onClick={() => setSelQuality(quality.value)}
                >
                  <strong>{quality.label}</strong>
                  <span>{quality.hint}</span>
                </button>
              ))}
            </div>
            <div className={`model-status ${curProvider?.configured ? "ok" : "bad"}`}>
              {curProvider?.configured ? "已连接" : "未配置"}
            </div>
            <p className="dock-note">{providerQualityNote}</p>
          </section>

          <section className="dock-section ck-panel">
            <div className="dock-title">设计师补充</div>
            <div className="form-group">
              <label>可选提示词</label>
              <textarea
                value={designerPrompt}
                onChange={(event) => setDesignerPrompt(event.target.value)}
                placeholder="只在需要时补充，例如：卷曲纱线头发、粉色心形贴布、高级商品棚拍。"
              />
            </div>
            <p className="dock-note">默认提示词保持简短，细节由设计师按项目补充。</p>
          </section>

          {activeTab === "modify" && (
            <section className="dock-section ck-panel">
              <div className="dock-title">主图修版</div>
              <div className="form-group">
                <label>修改说明</label>
                <textarea
                  value={modifyText}
                  onChange={(event) => setModifyText(event.target.value)}
                  placeholder="例如：把耳朵放大 20%，眼睛改成蓝色。"
                />
              </div>
              <div className="form-group">
                <label>保持不变区域</label>
                <input
                  value={lockedRegions}
                  onChange={(event) => setLockedRegions(event.target.value)}
                  placeholder="例如：身体轮廓、服装颜色、头部比例。"
                />
              </div>
            </section>
          )}
        </aside>

        <main className="sample-stage ck-stage">
          <div className="stage-toolbar ck-stage-toolbar">
            <div>
              <span className="stage-label">{activeStep.label}</span>
              <h3>{stageTitle(activeTab)}</h3>
              <p>{activeStep.note}</p>
            </div>
            <div className="stage-actions">
              {activeTab === "main" && (
                <button className="btn btn-primary" onClick={() => handleGenerate("main", "main_view_candidate")} disabled={generating}>
                  {generating ? "生成中..." : "生成主视图"}
                </button>
              )}
              {activeTab === "modify" && (
                <button className="btn btn-primary" onClick={() => handleGenerate("main", "local_modify")} disabled={generating || !selectedId || !modifyText.trim()}>
                  {generating ? "生成中..." : "应用主图修版"}
                </button>
              )}
              {activeTab === "multiview" && (
                <button className="btn btn-primary" onClick={handleBatchMultiview} disabled={generating || !selectedId || !selectedIsConfirmedMain}>
                  {generating ? "生成中..." : "生成三视图"}
                </button>
              )}
              {activeTab === "export" && (
                <>
                  <button className="btn btn-primary" onClick={handleExport}>客户确认图</button>
                  <button className="btn btn-outline" onClick={handleFactoryPdf}>工厂 PDF</button>
                  <button className="btn btn-outline" onClick={handlePackage}>工厂 ZIP</button>
                </>
              )}
            </div>
          </div>

          {generating && <div className="studio-progress">正在生成样品图，通常需要 1-3 分钟</div>}

          {activeTab !== "export" && (
            <section className="hero-sample-card ck-canvas-card">
              {selectedGeneration?.file_path ? (
                <img src={imageUrl(selectedGeneration.file_path)} alt="当前样品图" />
              ) : (
                <div className="sample-placeholder">
                  <strong>等待生成样品</strong>
                  <span>确认 brief 后，从左侧选择模型开始生成。</span>
                </div>
              )}
              <div className="sample-caption">
                <span>{selectedGeneration ? `Version #${selectedGeneration.id}` : "No version"}</span>
                <span>{selectedGeneration?.provider || selProvider} / {selectedGeneration?.provider_model || selectedQuality?.label || "-"}</span>
                <span>{selectedGeneration?.duration ? `${selectedGeneration.duration}s` : selectedIsConfirmedMain ? "已确认主图" : "需确认主图"}</span>
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
              compactTitle="主图修版轨道"
            />
          )}

          {activeTab === "multiview" && (
            <div className="multiview-stage ck-multiview">
              <ViewSlot label="正面 Front" generation={latestFront} imageUrl={imageUrl} onMaskEdit={setMaskEditor} />
              <ViewSlot label="侧面 Side" generation={latestSide} imageUrl={imageUrl} onMaskEdit={setMaskEditor} />
              <ViewSlot label="背面 Back" generation={latestBack} imageUrl={imageUrl} onMaskEdit={setMaskEditor} />
            </div>
          )}

          {activeTab === "export" && (
            <div className="export-stage ck-export-card">
              {boardPath ? (
                <img src={imageUrl(boardPath)} alt="客户确认图" />
              ) : (
                <div className="sample-placeholder">
                  <strong>{hasAllViews ? "可以生成客户确认图" : "三视图还不完整"}</strong>
                  <span>{hasAllViews ? "客户确认图只包含主图、正面、侧面和背面。" : "请先生成正面、侧面和背面视图，再导出确认图。"}</span>
                </div>
              )}
              {factoryPdfPath && <div className="export-path">工厂 PDF 已导出：{factoryPdfPath}</div>}
              {packagePath && <div className="export-path">资料包已导出：{packagePath}</div>}
            </div>
          )}
        </main>

        <aside className="version-dock ck-right-panel">
          <section className="dock-section ck-panel">
            <div className="dock-title">当前版本</div>
            {selectedGeneration ? (
              <div className="version-inspector">
                <strong>#{selectedGeneration.id}</strong>
                <span>{VIEW_LABELS[selectedGeneration.view_type] || selectedGeneration.view_type}</span>
                <span>{selectedGeneration.provider}/{selectedGeneration.provider_model || selectedGeneration.model_name || "-"}</span>
                <span>{selectedGeneration.quality_mode || "-"}</span>
                <span>{selectedIsConfirmedMain ? "已确认主图" : "未确认主图"}</span>
                {selectedGeneration.brief_id && <span>brief #{selectedGeneration.brief_id}</span>}
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
          </section>

          <section className="dock-section ck-panel">
            <div className="dock-title">订单要点</div>
            <dl className="brief-list">
              <div><dt>角色</dt><dd>{order.character_type || "-"}</dd></div>
              <div><dt>关键特征</dt><dd>{order.key_features || "-"}</dd></div>
              <div><dt>材质</dt><dd>{order.material_preference || "短毛绒 / 刺绣 / 填充棉"}</dd></div>
              <div><dt>配件</dt><dd>{order.accessories || "-"}</dd></div>
            </dl>
          </section>

          <section className="dock-section ck-panel">
            <div className="dock-title">三视图检查</div>
            <div className="view-check-list">
              <span className={latestFront ? "done" : ""}>正面</span>
              <span className={latestSide ? "done" : ""}>侧面</span>
              <span className={latestBack ? "done" : ""}>背面</span>
            </div>
            <p className={hasAllViews ? "dock-success" : "dock-note"}>
              {hasAllViews ? "三视图齐全，可以导出确认图。" : selectedIsConfirmedMain ? "已确认主图，可以生成三视图。" : "请先确认主图版本。"}
            </p>
          </section>

          <details className="history-dock ck-panel" open>
            <summary>版本历史 ({generations.length})</summary>
            <div className="history-list">
              {generations.map((generation) => (
                <button
                  key={generation.id}
                  className={generation.id === selectedId ? "active" : ""}
                  onClick={() => generation.file_path && setSelectedId(generation.id)}
                >
                  <span>#{generation.id} {VIEW_LABELS[generation.view_type] || generation.view_type}</span>
                  <small>{generation.provider}/{generation.provider_model || generation.model_name || "-"}</small>
                </button>
              ))}
            </div>
          </details>
        </aside>
      </div>

      {maskEditor?.file_path && (
        <MaskRevisionModal
          generation={maskEditor}
          imageUrl={imageUrl}
          generating={generating}
          onClose={() => setMaskEditor(null)}
          onSubmit={handleMaskedRevision}
        />
      )}
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

function providerNote(provider: string) {
  if (provider === "comfyui") {
    return "本地 ComfyUI 适合草稿探索；最终商品质感建议使用更强的云端模型。";
  }
  if (provider === "openai") {
    return "GPT 图像模型适合高质量商品样品图，优先保留真实布料、刺绣和棚拍质感。";
  }
  if (provider === "agnes") {
    return "Agnes 适合图生图样品探索，提示词保持短，主要依赖参考图。";
  }
  return "Replicate 适合作为云端备用模型，效果取决于所选模型和账户额度。";
}

function stageTitle(tab: Tab) {
  if (tab === "main") return "主样品候选";
  if (tab === "modify") return "定向修版";
  if (tab === "multiview") return "工厂三视图";
  return "交付输出";
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
                <button className="btn btn-outline btn-sm" onClick={(event) => { event.stopPropagation(); onConfirm(generation.id); }}>
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
  onMaskEdit,
}: {
  label: string;
  generation?: Generation;
  imageUrl: (filePath: string) => string;
  onMaskEdit: (generation: Generation) => void;
}) {
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

function MaskRevisionModal({
  generation,
  imageUrl,
  generating,
  onClose,
  onSubmit,
}: {
  generation: Generation;
  imageUrl: (filePath: string) => string;
  generating: boolean;
  onClose: () => void;
  onSubmit: (generation: Generation, maskDataUrl: string, prompt: string) => void;
}) {
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
