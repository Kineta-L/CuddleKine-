import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ordersApi, type Order } from "../api/client";
import { getErrorMessage } from "../utils/errors";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  material_imported: "素材已导入",
  brief_pending: "待确认",
  brief_confirmed: "已确认",
  generating: "生成中",
  reviewing: "审核中",
  exported: "已导出",
  archived: "已归档",
};

export default function OrderList() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const navigate = useNavigate();

  const loadOrders = async () => {
    setLoading(true);
    try {
      const data = await ordersApi.list();
      setOrders(data);
      setLoaded(true);
    } catch (error: unknown) {
      alert(`加载失败: ${getErrorMessage(error)}\n请确认后端服务已启动（端口 8765）。`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const order = await ordersApi.create({});
      navigate(`/orders/${order.id}`);
    } catch (error: unknown) {
      alert(`创建失败: ${getErrorMessage(error)}`);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确认删除这个订单？")) return;
    try {
      await ordersApi.delete(id);
      setOrders(orders.filter((order) => order.id !== id));
    } catch (error: unknown) {
      alert(`删除失败: ${getErrorMessage(error)}`);
    }
  };

  if (!loaded) {
    return (
      <div className="order-home">
        <section className="order-home-hero">
          <span>CuddleKine Atelier</span>
          <h2>毛绒玩具样品设计工作台</h2>
          <p>从客户参考图、聊天记录和文字需求开始，整理 brief、生成主图、修版三视图，并导出客户确认图与工厂生产资料。</p>
          <div className="order-home-actions">
            <button className="btn btn-primary" onClick={handleCreate}>新建设计订单</button>
            <button className="btn btn-outline" onClick={loadOrders} disabled={loading}>
              {loading ? "加载中..." : "加载已有订单"}
            </button>
          </div>
        </section>

        <section className="order-home-flow">
          {["导入素材", "确认 brief", "生成样品", "修版三视图", "导出资料"].map((step, index) => (
            <div key={step}>
              <strong>{String(index + 1).padStart(2, "0")}</strong>
              <span>{step}</span>
            </div>
          ))}
        </section>
      </div>
    );
  }

  return (
    <div className="order-library">
      <header className="library-header">
        <div>
          <span>CuddleKine Projects</span>
          <h2>设计订单</h2>
          <p>{orders.length} 个项目正在样品流程中</p>
        </div>
        <div className="library-actions">
          <button className="btn btn-outline btn-sm" onClick={loadOrders} disabled={loading}>刷新</button>
          <button className="btn btn-primary" onClick={handleCreate}>新建订单</button>
        </div>
      </header>

      {orders.length === 0 ? (
        <div className="empty-state">
          <p>暂无订单，点击“新建订单”开始第一个毛绒样品项目。</p>
        </div>
      ) : (
        <section className="order-card-grid">
          {orders.map((order) => (
            <article key={order.id} className="order-project-card">
              <div className="order-project-head">
                <span className={`status-badge status-${order.status}`}>
                  {STATUS_LABELS[order.status] || order.status}
                </span>
                <button className="btn btn-outline btn-sm" onClick={() => handleDelete(order.id)}>删除</button>
              </div>
              <Link to={`/orders/${order.id}`} className="order-project-title">
                {order.order_number}
              </Link>
              <dl>
                <div><dt>客户</dt><dd>{order.customer_name || "未填写"}</dd></div>
                <div><dt>角色</dt><dd>{order.character_type || "未填写"}</dd></div>
                <div><dt>尺寸</dt><dd>{order.target_height ? `${order.target_height}cm` : "待定"}</dd></div>
              </dl>
              <p>{order.key_features || order.source_summary || "等待导入参考素材和设计需求。"}</p>
              <div className="order-project-foot">
                <span>{order.created_at?.slice(0, 10)}</span>
                <Link className="btn btn-primary btn-sm" to={`/orders/${order.id}`}>进入项目</Link>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
