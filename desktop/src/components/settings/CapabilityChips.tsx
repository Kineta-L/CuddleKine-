import type { ProviderInfo } from "../../api/client";

interface CapabilityChipsProps {
  provider?: ProviderInfo;
  compact?: boolean;
}

export default function CapabilityChips({ provider, compact = false }: CapabilityChipsProps) {
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
