import type { DamageTier } from "@/lib/types";

const tierClasses: Record<DamageTier | "critical" | "severe-label", string> = {
  intact: "bg-status-intact/15 text-status-intact",
  minor: "bg-status-minor/15 text-status-minor",
  moderate: "bg-status-moderate/15 text-status-moderate",
  severe: "bg-status-severe text-white",
  destroyed: "bg-status-destroyed text-white",
  critical: "bg-status-destroyed text-white",
  "severe-label": "bg-status-severe text-white"
};

export function SeverityBadge({ label }: { label: string }) {
  const key = label.toLowerCase().includes("critical")
    ? "critical"
    : label.toLowerCase().includes("severe")
      ? "severe-label"
      : (label.toLowerCase() as DamageTier);
  return (
    <span className={`rounded px-2 py-1 font-mono text-[10px] font-bold uppercase tracking-wide ${tierClasses[key] ?? tierClasses.moderate}`}>
      {label}
    </span>
  );
}
