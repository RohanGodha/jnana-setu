export const ANUYOGA_CONFIG: Record<string, { label: string; color: string }> = {
  dravyanuyog: { label: "Philosophy", color: "#7C6AE8" },
  charananuyog: { label: "Ethics", color: "#3B9E75" },
  prathamanuyoga: { label: "History", color: "#C97A3A" },
  karnanuyoga: { label: "Cosmology", color: "#4A8FC9" },
  all_texts: { label: "All Texts", color: "#8C8880" },
};

export function AnuyogaBadge({ anuyoga }: { anuyoga: string }) {
  const cfg = ANUYOGA_CONFIG[anuyoga] ?? ANUYOGA_CONFIG.all_texts;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${cfg.color}1A`, color: cfg.color }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: cfg.color }}
      />
      {cfg.label}
    </span>
  );
}
