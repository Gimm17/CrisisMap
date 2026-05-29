import type { LucideIcon } from "lucide-react";

type Props = {
  label: string;
  value: string;
  helper?: string;
  icon: LucideIcon;
  tone?: "default" | "warning" | "danger";
};

export function StatCard({ label, value, helper, icon: Icon, tone = "default" }: Props) {
  const color = tone === "danger" ? "text-status-severe" : tone === "warning" ? "text-status-minor" : "text-on-surface";
  const border = tone === "danger" ? "border-status-severe" : "border-outline-variant";
  return (
    <div className={`rounded-lg border ${border} bg-surface-container-lowest p-4 shadow-panel`}>
      <div className="flex items-center gap-2">
        <Icon className={`h-4 w-4 ${tone === "default" ? "text-outline" : color}`} />
        <span className="font-mono text-label-mono uppercase text-on-surface-variant">{label}</span>
      </div>
      <div className={`mt-3 text-stat-value ${color}`}>{value}</div>
      {helper ? <p className="text-body-sm text-outline">{helper}</p> : null}
    </div>
  );
}
