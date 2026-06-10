import type { ProviderInfo } from "../../api/client";
import CapabilityChips from "./CapabilityChips";

interface ProviderConfigCardProps {
  provider?: ProviderInfo;
  title: string;
  status: boolean;
  bestFor: string;
  cost: string;
  secretLabel: string;
  secretPlaceholder: string;
  secretValue: string;
  onSecretChange: (value: string) => void;
}

export default function ProviderConfigCard({
  provider,
  title,
  status,
  bestFor,
  cost,
  secretLabel,
  secretPlaceholder,
  secretValue,
  onSecretChange,
}: ProviderConfigCardProps) {
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
          onChange={(event) => onSecretChange(event.target.value)}
        />
      </div>
    </section>
  );
}
