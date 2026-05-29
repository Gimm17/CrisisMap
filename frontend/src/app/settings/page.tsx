"use client";

import { useEffect, useState } from "react";
import type { ElementType, ReactNode } from "react";
import { CheckCircle2, Eye, Group, Save, Server, Settings2, ShieldCheck, Satellite, TriangleAlert, UserCheck, UserPlus } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { getAnalysisSettings, getDataSourceStatus, updateAnalysisSettings } from "@/lib/api";
import { TOKENROUTER_MODELS } from "@/lib/settings";
import type { AnalysisSettings, DataSourceReadiness, DataSourceReadinessItem, ProcessingPriority } from "@/lib/types";

const fallbackSettings: AnalysisSettings = {
  model_profile: "damage",
  tokenrouter_model: "anthropic/claude-sonnet-4.6",
  confidence_threshold: 85,
  processing_priority: "standard",
  raw_imagery_retention_days: 90,
  scrub_metadata_on_export: false,
  auto_publish_destroyed_tags: true,
  provider_status: "missing-key",
  tokenrouter_base_url: "https://api.tokenrouter.com/v1"
};

type TeamRole = "Admin" | "Analyst" | "Viewer";
type TeamMember = {
  id: string;
  initials: string;
  name: string;
  role: TeamRole;
  status: "active" | "suspended" | "pending";
  lastActive: string;
};

const initialTeamMembers: TeamMember[] = [
  { id: "jane", initials: "JD", name: "Jane Doe", role: "Admin", status: "active", lastActive: "2 min ago" },
  { id: "alex", initials: "AR", name: "Alex Rodriguez", role: "Analyst", status: "active", lastActive: "18 min ago" },
  { id: "sarah", initials: "SM", name: "Sarah Miller", role: "Viewer", status: "pending", lastActive: "Invited" }
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<AnalysisSettings>(fallbackSettings);
  const [showProviderHint, setShowProviderHint] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>(initialTeamMembers);
  const [selectedMemberId, setSelectedMemberId] = useState(initialTeamMembers[0].id);
  const [sourceReadiness, setSourceReadiness] = useState<DataSourceReadiness>({});

  useEffect(() => {
    void getAnalysisSettings(fallbackSettings).then(setSettings);
    void getDataSourceStatus().then(setSourceReadiness);
  }, []);

  const selectedMember = teamMembers.find((member) => member.id === selectedMemberId) ?? teamMembers[0];

  function patchSettings(patch: Partial<AnalysisSettings>) {
    setSettings((current) => ({ ...current, ...patch }));
    setSaveState("idle");
  }

  function patchConfidenceThreshold(value: number) {
    if (Number.isNaN(value)) return;
    patchSettings({ confidence_threshold: Math.min(99, Math.max(50, value)) });
  }

  async function saveSettings() {
    setSaveState("saving");
    try {
      const next = await updateAnalysisSettings(settings);
      setSettings((current) => ({ ...current, ...next }));
      setSaveState("saved");
    } catch {
      setSaveState("failed");
    }
  }

  function updateSelectedRole(role: TeamRole) {
    setTeamMembers((current) => current.map((member) => (member.id === selectedMember.id ? { ...member, role } : member)));
  }

  function toggleSelectedStatus() {
    setTeamMembers((current) =>
      current.map((member) =>
        member.id === selectedMember.id
          ? {
              ...member,
              status: member.status === "suspended" ? "active" : "suspended",
              lastActive: member.status === "suspended" ? "Just reactivated" : "Suspended"
            }
          : member
      )
    );
  }

function inviteAnalyst() {
    const pendingCount = teamMembers.filter((member) => member.status === "pending").length + 1;
    const id = `pending-${Date.now()}`;
    const member: TeamMember = {
      id,
      initials: `N${pendingCount}`,
      name: `New Analyst ${pendingCount}`,
      role: "Analyst",
      status: "pending",
      lastActive: "Invitation drafted"
    };
    setTeamMembers((current) => [...current, member]);
    setSelectedMemberId(id);
  }

  return (
    <AppShell sidebar={false}>
      <div className="h-full overflow-y-auto p-8 pb-24">
        <div className="mb-10 flex items-start justify-between">
          <div>
            <h1 className="text-headline-lg">Operational Settings</h1>
            <p className="mt-2 text-body-md text-on-surface-variant">Manage system integrations, team access, and processing parameters.</p>
          </div>
          <button onClick={saveSettings} className="flex items-center gap-2 rounded bg-primary px-6 py-3 font-mono text-label-mono uppercase text-on-primary">
            <Save className="h-4 w-4" />
            {saveState === "saving" ? "Saving" : "Save Changes"}
          </button>
        </div>

        {saveState !== "idle" ? (
          <div className={`mb-5 rounded border px-4 py-3 font-mono text-label-mono uppercase ${saveState === "failed" ? "border-status-destroyed bg-status-destroyed/10 text-status-destroyed" : "border-status-intact bg-status-intact/10 text-status-intact"}`}>
            {saveState === "saved" ? "Settings saved" : saveState === "failed" ? "Settings failed to save" : "Saving settings"}
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[1fr_400px]">
          <div className="space-y-6">
            <Card title="Imagery & AI Providers" icon={Satellite}>
              <ProviderRow
                label="TokenRouter API"
                value={showProviderHint ? "Configured server-side only" : "************************"}
                status={sourceReadiness.tokenrouter?.status === "configured" || settings.provider_status === "configured" ? "Active" : "Missing Key"}
                onReveal={() => setShowProviderHint((value) => !value)}
              />
              <ProviderRow label="TokenRouter Base URL" value={settings.tokenrouter_base_url ?? fallbackSettings.tokenrouter_base_url!} status="Configurable" warning />
              <ProviderRow label="PostGIS Persistence" value={String(sourceReadiness.postgis?.backend ?? "json fallback")} status={providerStatus(sourceReadiness.postgis)} warning={sourceReadiness.postgis?.status !== "ready"} />
              <ProviderRow label="OSM / Overpass" value={statusValue(sourceReadiness.osm)} status={providerStatus(sourceReadiness.osm)} warning={sourceReadiness.osm?.status !== "ready"} />
              <ProviderRow label="HDX Local Layers" value={statusValue(sourceReadiness.hdx)} status={providerStatus(sourceReadiness.hdx)} warning={sourceReadiness.hdx?.status !== "ready"} />
              <ProviderRow label="Maxar Pre/Post Imagery" value={imageryStatus(sourceReadiness)} status={imageryProviderStatus(sourceReadiness)} warning={imageryProviderStatus(sourceReadiness) !== "Active"} />
              <ProviderRow
                label="SiamUnet ML Inference"
                value={String(sourceReadiness.ml_model?.message ?? sourceReadiness.ml_model?.checkpoint_path ?? "not checked")}
                status={providerStatus(sourceReadiness.ml_model)}
                warning={sourceReadiness.ml_model?.status !== "ready"}
              />
              <ProviderRow label="xBD Dataset" value={xbdStatus(sourceReadiness)} status={xbdProviderStatus(sourceReadiness)} warning={xbdProviderStatus(sourceReadiness) !== "Active"} />
              <ProviderRow label="Copernicus Sentinel" value="credential-aware placeholder" status={sourceReadiness.sentinel?.status === "ready" ? "Active" : "Needs Credentials"} warning={sourceReadiness.sentinel?.status !== "ready"} />
            </Card>

            <Card title="Analysis Engine Parameters" icon={Settings2}>
              <div className="grid gap-8 md:grid-cols-2">
                <div>
                  <label className="font-mono text-label-mono uppercase">Damage Assessment Model</label>
                  <select
                    className="mt-3 w-full rounded border border-outline-variant bg-white px-3 py-2"
                    value={settings.model_profile}
                    onChange={(event) => patchSettings({ model_profile: event.target.value })}
                  >
                    <option value="damage">Building Damage V4.2 (High Precision)</option>
                    <option value="flood">Flood Extent Mapper</option>
                    <option value="fire">Thermal Scan V1</option>
                  </select>

                  <label className="mt-7 block font-mono text-label-mono uppercase">TokenRouter Model</label>
                  <select
                    className="mt-3 w-full rounded border border-outline-variant bg-white px-3 py-2"
                    value={settings.tokenrouter_model}
                    onChange={(event) => patchSettings({ tokenrouter_model: event.target.value as AnalysisSettings["tokenrouter_model"] })}
                  >
                    {TOKENROUTER_MODELS.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>

                  <label className="mt-7 block font-mono text-label-mono uppercase">Processing Priority</label>
                  <div className="mt-3 grid grid-cols-3 rounded bg-surface-container-highest p-1">
                    {(["economy", "standard", "critical"] as ProcessingPriority[]).map((value) => (
                      <button
                        key={value}
                        onClick={() => patchSettings({ processing_priority: value })}
                        className={`rounded py-2 capitalize ${settings.processing_priority === value ? "bg-white font-semibold shadow-sm" : "text-on-surface-variant"}`}
                      >
                        {value}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="flex justify-between">
                    <label className="font-mono text-label-mono uppercase">Confidence Threshold</label>
                    <span className="font-mono text-label-mono text-primary">{settings.confidence_threshold}%</span>
                  </div>
                  <input
                    className="mt-4 w-full accent-primary"
                    type="range"
                    min={50}
                    max={99}
                    value={settings.confidence_threshold}
                    onChange={(event) => patchConfidenceThreshold(Number(event.target.value))}
                    onInput={(event) => patchConfidenceThreshold(Number(event.currentTarget.value))}
                  />
                  <input
                    aria-label="Confidence Threshold Value"
                    className="mt-3 w-24 rounded border border-outline-variant bg-white px-3 py-2 text-body-sm"
                    type="number"
                    min={50}
                    max={99}
                    value={settings.confidence_threshold}
                    onChange={(event) => patchConfidenceThreshold(Number(event.target.value))}
                  />
                  <p className="mt-2 text-body-sm text-on-surface-variant">Detections below this percentage will be flagged for human review.</p>
                  <label className="mt-7 flex items-center gap-3 rounded border border-outline-variant bg-surface p-4">
                    <input
                      type="checkbox"
                      checked={settings.auto_publish_destroyed_tags}
                      onChange={(event) => patchSettings({ auto_publish_destroyed_tags: event.target.checked })}
                      className="h-4 w-4 accent-primary"
                    />
                    Auto-publish 'Destroyed' structural tags
                  </label>
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <Card title="Active Team" icon={Group} compact>
              <div className="mb-4 flex items-center justify-between gap-3">
                <p className="text-body-sm text-on-surface-variant">{teamMembers.filter((member) => member.status === "active").length} active operators</p>
                <button onClick={inviteAnalyst} className="flex items-center gap-1 rounded border border-outline-variant px-3 py-2 font-mono text-label-mono uppercase text-primary">
                  <UserPlus className="h-4 w-4" />
                  Invite
                </button>
              </div>
              {teamMembers.map((member) => (
                <button
                  key={member.id}
                  onClick={() => setSelectedMemberId(member.id)}
                  className={`flex w-full items-center gap-3 border-b border-outline-variant py-4 text-left last:border-b-0 ${selectedMember.id === member.id ? "text-primary" : "text-on-surface"}`}
                >
                  <span className={`flex h-10 w-10 items-center justify-center rounded-full ${member.status === "suspended" ? "bg-outline-variant text-on-surface-variant" : "bg-primary text-on-primary"}`}>
                    {member.initials}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{member.name}</p>
                    <p className="font-mono text-label-mono text-on-surface-variant">{member.role} - {member.lastActive}</p>
                  </div>
                  <span className={`rounded px-2 py-1 font-mono text-[10px] uppercase ${member.status === "active" ? "bg-status-intact/15 text-status-intact" : member.status === "pending" ? "bg-status-minor/20 text-status-minor" : "bg-status-destroyed/10 text-status-destroyed"}`}>
                    {member.status}
                  </span>
                </button>
              ))}
              <div className="mt-5 rounded border border-outline-variant bg-surface p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-label-mono uppercase text-primary">Selected Member</p>
                    <p className="mt-1 font-semibold">{selectedMember.name}</p>
                  </div>
                  <ShieldCheck className="h-5 w-5 text-primary" />
                </div>
                <label className="mt-4 block font-mono text-label-mono uppercase text-on-surface-variant">
                  Role
                  <select
                    className="mt-2 w-full rounded border border-outline-variant bg-white px-3 py-2 text-body-sm normal-case"
                    value={selectedMember.role}
                    onChange={(event) => updateSelectedRole(event.target.value as TeamRole)}
                  >
                    <option value="Admin">Admin</option>
                    <option value="Analyst">Analyst</option>
                    <option value="Viewer">Viewer</option>
                  </select>
                </label>
                <button onClick={toggleSelectedStatus} className="mt-4 flex w-full items-center justify-center gap-2 rounded bg-surface-container px-3 py-2 font-mono text-label-mono uppercase text-primary">
                  <UserCheck className="h-4 w-4" />
                  {selectedMember.status === "suspended" ? "Reactivate Access" : "Suspend Access"}
                </button>
              </div>
            </Card>

            <Card title="Data Retention" icon={Server} compact>
              <label className="font-mono text-label-mono uppercase">Raw Imagery Storage</label>
              <select
                className="mt-3 w-full rounded border border-outline-variant bg-surface px-3 py-2"
                value={settings.raw_imagery_retention_days}
                onChange={(event) => patchSettings({ raw_imagery_retention_days: Number(event.target.value) })}
              >
                <option value={90}>90 Days (Standard)</option>
                <option value={30}>30 Days</option>
                <option value={180}>180 Days</option>
              </select>
              <label className="mt-7 flex gap-3">
                <input
                  type="checkbox"
                  checked={settings.scrub_metadata_on_export}
                  onChange={(event) => patchSettings({ scrub_metadata_on_export: event.target.checked })}
                  className="mt-1 h-4 w-4 accent-primary"
                />
                <span>
                  <strong className="block">Scrub metadata on export</strong>
                  <span className="text-body-sm text-on-surface-variant">Automatically remove geo-coordinates and timestamp EXIF data from generated reports.</span>
                </span>
              </label>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function providerStatus(item?: DataSourceReadinessItem): string {
  if (!item?.status) return "Unknown";
  if (item.status === "ready" || item.status === "configured") return "Active";
  if (item.status === "needs_credentials") return "Needs Credentials";
  if (item.status === "fallback") return "Fallback";
  if (item.status === "warning") return "Warning";
  return "Missing";
}

function statusValue(item?: DataSourceReadinessItem): string {
  if (!item) return "not checked";
  if (item.counts) {
    return Object.entries(item.counts)
      .slice(0, 3)
      .map(([key, value]) => `${key}: ${value}`)
      .join(", ");
  }
  return String(item.message ?? item.path ?? item.status ?? "not checked");
}

function imageryProviderStatus(readiness: DataSourceReadiness): string {
  const pre = readiness.imagery?.maxar_pre?.status;
  const post = readiness.imagery?.maxar_post?.status;
  return pre === "ready" && post === "ready" ? "Active" : "Missing";
}

function imageryStatus(readiness: DataSourceReadiness): string {
  const pre = readiness.imagery?.maxar_pre?.status ?? "unknown";
  const post = readiness.imagery?.maxar_post?.status ?? "unknown";
  return `pre: ${pre}, post: ${post}`;
}

function xbdProviderStatus(readiness: DataSourceReadiness): string {
  const train = readiness.xbd?.train;
  const tier3 = readiness.xbd?.tier3;
  return train?.valid || tier3?.valid ? "Active" : "Missing";
}

function xbdStatus(readiness: DataSourceReadiness): string {
  const trainCount = readiness.xbd?.train?.sampled_tiles ?? readiness.xbd?.train?.paired_tiles ?? 0;
  const tier3Count = readiness.xbd?.tier3?.sampled_tiles ?? readiness.xbd?.tier3?.paired_tiles ?? 0;
  return `train sample: ${trainCount}, tier3 sample: ${tier3Count}`;
}

function Card({ title, icon: Icon, children, compact = false }: { title: string; icon: ElementType; children: ReactNode; compact?: boolean }) {
  return (
    <section className="rounded-lg border border-outline-variant bg-white shadow-panel">
      <header className="flex items-center gap-3 border-b border-outline-variant p-6">
        <Icon className="h-6 w-6 text-primary" />
        <h2 className={compact ? "text-headline-sm" : "text-headline-md"}>{title}</h2>
      </header>
      <div className={compact ? "p-6" : "p-8"}>{children}</div>
    </section>
  );
}

function ProviderRow({ label, value, status, warning = false, onReveal }: { label: string; value: string; status: string; warning?: boolean; onReveal?: () => void }) {
  const [copied, setCopied] = useState(false);

  async function handleAction() {
    if (onReveal) {
      onReveal();
      return;
    }
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // Clipboard can be blocked in some embedded browsers; keep the control responsive.
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="mb-6 last:mb-0">
      <div className="mb-2 flex justify-between">
        <label className="font-mono text-label-mono uppercase">{label}</label>
        <span className={`flex items-center gap-1 font-mono text-label-mono ${warning ? "text-status-minor" : status === "Active" ? "text-status-intact" : "text-status-severe"}`}>
          {warning ? <TriangleAlert className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
          {status}
        </span>
      </div>
      <div className="flex gap-3">
        <input className="flex-1 rounded border border-outline-variant bg-surface-container-lowest px-3 py-2" readOnly value={value} />
        <button onClick={handleAction} className="rounded border border-outline-variant bg-surface-container px-4 py-2" aria-label={onReveal ? `Toggle ${label} visibility` : `Copy ${label}`}>
          <Eye className="h-5 w-5" />
        </button>
      </div>
      {copied ? <p className="mt-2 font-mono text-label-mono uppercase text-status-intact">Copied</p> : null}
    </div>
  );
}
