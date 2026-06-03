/** API 客户端 — 与 Python 后端通信 */
const BASE_URL = "http://127.0.0.1:8765";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ========== 订单 ==========
export interface Order {
  id: number;
  order_number: string;
  customer_name: string | null;
  character_type: string | null;
  target_height: number | null;
  main_proportions: string | null;
  colors: string | null;
  material_preference: string | null;
  accessories: string | null;
  key_features: string | null;
  allowed_simplifications: string | null;
  pending_items: string | null;
  craft_notes: string | null;
  status: string;
  confirmed_version_id: number | null;
  created_at: string;
  updated_at: string;
}

export const ordersApi = {
  list: (status?: string) =>
    request<Order[]>(`/api/orders/${status ? `?status=${status}` : ""}`),
  get: (id: number) => request<Order>(`/api/orders/${id}`),
  create: (data: Partial<Order>) =>
    request<Order>("/api/orders/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: Partial<Order>) =>
    request<Order>(`/api/orders/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: number) =>
    request<{ message: string }>(`/api/orders/${id}`, { method: "DELETE" }),
};

// ========== 素材 ==========
export interface Material {
  id: number;
  order_id: number;
  type: string;
  file_path: string | null;
  original_name: string | null;
  ocr_text: string | null;
  notes: string | null;
  created_at: string;
}

export const materialsApi = {
  list: (orderId: number) => request<Material[]>(`/api/materials/${orderId}`),
  upload: async (orderId: number, file: File, type: string, notes?: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("material_type", type);
    if (notes) form.append("notes", notes);
    const res = await fetch(`${BASE_URL}/api/materials/${orderId}/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "上传失败" }));
      throw new Error(err.detail || "上传失败");
    }
    return res.json() as Promise<Material>;
  },
  delete: (id: number) =>
    request<{ message: string }>(`/api/materials/${id}`, { method: "DELETE" }),
};

// ========== Brief ==========
export interface Brief {
  id: number;
  order_id: number;
  version: number;
  is_confirmed: boolean;
  structured_content: string | null;
  missing_info: string | null;
  conflicts: string | null;
  customer_replies: string | null;
  summary: string;
  created_at: string;
  updated_at: string;
}

export const briefsApi = {
  analyze: (orderId: number) =>
    request<Brief>(`/api/briefs/${orderId}/analyze`, { method: "POST" }),
  reply: (briefId: number, replies: Record<string, string>) =>
    request<Brief>(`/api/briefs/${briefId}/reply`, {
      method: "PUT",
      body: JSON.stringify({ replies }),
    }),
  list: (orderId: number) => request<Brief[]>(`/api/briefs/${orderId}`),
};

// ========== Provider 信息 ==========
export interface ProviderInfo {
  id: string;
  name: string;
  enabled: boolean;
  configured: boolean;
  supports_text_to_image: boolean;
  supports_image_to_image: boolean;
  supports_inpaint: boolean;
  supports_transparent_background: boolean;
  models: { id: string; name: string; quality: string; best_for: string }[];
}

export const providersApi = {
  list: () => request<ProviderInfo[]>("/api/generation/providers"),
};

// ========== 设置 ==========
export interface AppSettings {
  default_provider: string;
  default_model: string;
  default_quality: string;
  transparent_background: boolean;
  openai_configured: boolean;
  replicate_configured: boolean;
  comfyui_base_url: string;
  comfyui_input_dir: string;
  settings_path: string;
}

export const settingsApi = {
  get: () => request<AppSettings>("/api/settings"),
  update: (data: Partial<AppSettings> & {
    openai_api_key?: string;
    replicate_api_token?: string;
  }) =>
    request<AppSettings>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

// ========== 生成 ==========
export interface Generation {
  id: number;
  order_id: number;
  provider: string;
  provider_model: string;
  quality_mode: string;
  source_version_id: number | null;
  derivation_type: string | null;
  view_type: string;
  file_path: string | null;
  locked_regions: string | null;
  model_name: string | null;
  license_status: string | null;
  workflow_version: string | null;
  duration: number | null;
  error_message: string | null;
  created_at: string;
}

export const generationApi = {
  generate: (data: {
    order_id: number;
    provider?: string;
    model?: string;
    quality_mode?: string;
    workflow_name?: string;
    view_type?: string;
    derivation_type?: string;
    source_version_id?: number;
    locked_regions?: string;
    modification_prompt?: string;
    model_name?: string;
    reference_material_id?: number;
    transparent_background?: boolean;
    overrides?: Record<string, unknown>;
  }) =>
    request<Generation>("/api/generation/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  list: (orderId: number) => request<Generation[]>(`/api/generation/${orderId}`),
  confirm: (generationId: number) =>
    request<{ message: string }>(
      `/api/generation/${generationId}/confirm`,
      { method: "POST" }
    ),
  batchMultiview: (data: {
    order_id: number;
    source_version_id: number;
    provider?: string;
    model?: string;
    quality_mode?: string;
    transparent_background?: boolean;
  }) =>
    request<Generation[]>(
      "/api/generation/batch-multiview",
      { method: "POST", body: JSON.stringify(data) }
    ),
};

// ========== 导出 ==========
export interface ExportResult {
  board_path: string;
  message: string;
}

export interface ExportPackage {
  package_path: string;
  file_count: number;
  message: string;
}

export const exportApi = {
  board: (orderId: number) =>
    request<ExportResult>(`/api/export/${orderId}/board`, { method: "POST" }),
  package: (orderId: number) =>
    request<ExportPackage>(`/api/export/${orderId}/package`, { method: "POST" }),
};

// ========== 健康检查 ==========
export const healthCheck = () => request<{ status: string }>("/api/health");

export interface SystemStatus {
  backend: {
    status: string;
    host: string;
    port: number;
  };
  generation: {
    provider: string;
  };
  comfyui: {
    status: string;
    base_url: string;
    dir: string;
    dir_exists: boolean;
    uv_exe: string;
    uv_exe_exists: boolean;
    input_dir: string;
    input_dir_exists: boolean;
    workflow_dir: string;
    workflow_dir_exists: boolean;
  };
  storage: {
    data_dir: string;
    output_dir: string;
    data_dir_exists: boolean;
    output_dir_exists: boolean;
  };
}

export const statusApi = {
  get: () => request<SystemStatus>("/api/status"),
  startComfyUI: () =>
    request<{ status: string; message: string; pid?: number }>("/api/comfyui/start", {
      method: "POST",
    }),
};
