import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ordersApi, type Order } from "../api/client";

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
    } catch (e: any) {
      alert(`加载失败: ${e.message}\n请确认后端服务已启动 (端口 8765)`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const order = await ordersApi.create({});
      navigate(`/orders/${order.id}`);
    } catch (e: any) {
      alert(`创建失败: ${e.message}`);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确认删除该订单？")) return;
    try {
      await ordersApi.delete(id);
      setOrders(orders.filter((o) => o.id !== id));
    } catch (e: any) {
      alert(`删除失败: ${e.message}`);
    }
  };

  if (!loaded) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <h2>CuddleKine</h2>
        <p style={{ color: "#666", margin: "16px 0" }}>
          首版聚焦角色/IP 公仔：整理素材 → 生成效果图 → 局部修改 → 多视图 → 导出确认板
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
          <button className="btn btn-primary" onClick={handleCreate}>
            新建订单
          </button>
          <button className="btn btn-outline" onClick={loadOrders} disabled={loading}>
            {loading ? "加载中" : "加载已有订单"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2>订单列表 ({orders.length})</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-outline btn-sm" onClick={loadOrders} disabled={loading}>
            刷新
          </button>
          <button className="btn btn-primary" onClick={handleCreate}>
            新建订单
          </button>
        </div>
      </div>

      {orders.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📋</div>
          <p>暂无订单，点击"新建订单"开始</p>
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>订单号</th>
              <th>客户</th>
              <th>角色类型</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id}>
                <td>
                  <Link to={`/orders/${o.id}`} style={{ color: "#c93566", fontWeight: 800, textDecoration: "none" }}>
                    {o.order_number}
                  </Link>
                </td>
                <td>{o.customer_name || "-"}</td>
                <td>{o.character_type || "-"}</td>
                <td>
                  <span className={`status-badge status-${o.status}`}>
                    {STATUS_LABELS[o.status] || o.status}
                  </span>
                </td>
                <td>{o.created_at?.slice(0, 10)}</td>
                <td>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(o.id)}
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
