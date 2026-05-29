"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, Building2, CheckCircle2, Download, MemoryStick, Share2, UserCheck } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { API_BASE_URL, getAssessmentArtifacts, getBuildingChipUrl, getBuildingsGeoJson, getPriorities } from "@/lib/api";
import { demoPriorities } from "@/lib/demo";
import { formatNumber } from "@/lib/format";
import type { AssessmentArtifacts, BuildingFeatureCollection, PriorityBuilding } from "@/lib/types";

export default function PriorityBuildingPage() {
  const params = useParams<{ id: string }>();
  const buildingId = Array.isArray(params.id) ? params.id[0] : params.id;
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [priorities, setPriorities] = useState<PriorityBuilding[]>(demoPriorities);
  const [artifacts, setArtifacts] = useState<AssessmentArtifacts>({});
  const [geojson, setGeojson] = useState<BuildingFeatureCollection | null>(null);
  const [assigned, setAssigned] = useState(false);

  useEffect(() => {
    setAssessmentId(new URLSearchParams(window.location.search).get("assessment") ?? "demo");
  }, []);

  useEffect(() => {
    if (!assessmentId) return;
    let active = true;
    void Promise.all([getPriorities(assessmentId), getAssessmentArtifacts(assessmentId), getBuildingsGeoJson(assessmentId)]).then(
      ([nextPriorities, nextArtifacts, nextGeojson]) => {
        if (!active) return;
        setPriorities(nextPriorities);
        setArtifacts(nextArtifacts);
        setGeojson(nextGeojson);
      }
    );
    return () => {
      active = false;
    };
  }, [assessmentId]);

  const priority = useMemo(
    () => priorities.find((item) => item.building_id === buildingId) ?? priorities[0],
    [buildingId, priorities]
  );
  const buildingFeature = useMemo(
    () => geojson?.features.find((feature) => feature.properties.building_id === priority.building_id),
    [geojson, priority.building_id]
  );
  const buildingProps = buildingFeature?.properties;
  const chipArtifact = artifacts.chip_artifacts?.[priority.building_id];
  const hasEvidenceChips = Boolean(chipArtifact?.pre && chipArtifact?.post && assessmentId);
  const validationMetrics = artifacts.validation?.metrics;

  return (
    <AppShell sidebar={false}>
      <div className="h-full overflow-y-auto bg-surface p-5 pb-24">
        <div className="grid gap-5 xl:grid-cols-[480px_1fr]">
          <section className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest shadow-panel">
            <div className="bg-surface-container-low p-8">
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-headline-lg text-primary">{priority.name}</h1>
                  <p className="mt-1 flex items-center gap-1 text-body-md text-on-surface-variant">
                    <Building2 className="h-4 w-4" />
                    {priority.infrastructure_type} - Sector 7G
                  </p>
                </div>
                <span className="rounded bg-surface-container px-2 py-1 font-mono text-label-mono">RANK #{priority.rank}</span>
              </div>
              <div className="mt-6 flex items-center gap-5 rounded border border-status-destroyed bg-status-destroyed/15 p-5 text-status-destroyed">
                <AlertTriangle className="h-9 w-9" />
                <div>
                  <div className="text-headline-sm">Damage Score: {priority.damage_score}/100</div>
                  <div className="font-mono text-label-mono uppercase">Critical - Structural Failure</div>
                </div>
              </div>
            </div>

            <div className="space-y-6 border-t border-outline-variant p-8">
              <h2 className="text-headline-sm">Satellite Assessment</h2>
              {hasEvidenceChips && assessmentId ? (
                <div className="grid gap-3 md:grid-cols-2">
                  <EvidenceImage label="Before Chip" src={getBuildingChipUrl(assessmentId, priority.building_id, "pre")} />
                  <EvidenceImage label="After Chip" src={getBuildingChipUrl(assessmentId, priority.building_id, "post")} />
                </div>
              ) : (
                <div className="flex h-64 items-center justify-center rounded border border-dashed border-outline-variant bg-surface text-body-sm text-on-surface-variant">
                  Evidence chips are unavailable for this building.
                </div>
              )}
              <p className="text-body-md">
                <strong>Damage Notes:</strong> Prediction method is{" "}
                <span className="font-mono text-label-mono uppercase text-primary">{buildingProps?.inference_method ?? artifacts.method ?? "unknown"}</span>.
                {buildingProps?.validation_label ? ` Copernicus EMSR452 label: ${buildingProps.validation_label}.` : " No direct validation label was matched for this footprint."}
              </p>
            </div>

            <div className="bg-surface-container-low p-8">
              <h2 className="mb-5 flex items-center gap-2 text-headline-sm">
                <MemoryStick className="h-5 w-5 text-primary" />
                AI Analysis & Confidence
              </h2>
              <div className="flex items-center justify-between border-b border-outline-variant pb-3">
                <span className="font-mono text-label-mono uppercase text-on-surface-variant">Model Confidence</span>
                <span className="text-stat-value text-status-intact">{Math.round(priority.confidence * 100)}%</span>
              </div>
              <div className="mt-4 grid gap-3 text-body-sm">
                <EvidenceMetric label="Inference Method" value={buildingProps?.inference_method ?? artifacts.method ?? "unknown"} />
                <EvidenceMetric label="Model Version" value={buildingProps?.model_version ?? "baseline fallback"} />
                <EvidenceMetric
                  label="Validation Match"
                  value={buildingProps?.validation_match == null ? "unmatched" : buildingProps.validation_match ? "matched" : "different class"}
                />
                <EvidenceMetric label="Validation Macro F1" value={typeof validationMetrics?.macro_f1 === "number" ? validationMetrics.macro_f1.toFixed(3) : "n/a"} />
              </div>
              <h3 className="mt-5 font-mono text-label-mono uppercase text-on-surface-variant">Cascade Effect Analysis</h3>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-body-md">
                <li>{priority.reasoning}</li>
                <li>Surrounding support assets are expected to exceed capacity without rapid stabilization.</li>
                <li>Backup supply chains are likely compromised until road access is restored.</li>
              </ul>
            </div>
          </section>

          <section className="space-y-5">
            <Panel title="Humanitarian Impact">
              <div className="grid gap-4 md:grid-cols-3">
                <Impact label="Population Affected" value={`~${formatNumber(priority.affected_population)}`} helper="Primary catchment area" />
                <Impact label="Beds Lost" value={priority.infrastructure_type.includes("Medical") ? "450" : "n/a"} helper="Operational capacity" danger />
                <Impact label="Secondary Risk" value="High" helper="Cascade potential" warning />
              </div>
              <p className="mt-7 text-body-md">{priority.reasoning}</p>
            </Panel>

            <Panel title="Reconstruction Roadmap">
              <div className="grid gap-8 md:grid-cols-[1fr_1fr]">
                <div>
                  <Metric label="Est. Cost" value={`$${(priority.estimated_cost_usd / 1000000).toFixed(1)}M`} />
                  <Metric label="Timeline" value={`${priority.repair_timeline_days} Days`} />
                </div>
                <div>
                  <h3 className="mb-3 text-headline-sm">Required Specialists</h3>
                  <div className="flex flex-wrap gap-2">
                    {priority.required_specialists.map((specialist) => (
                      <span key={specialist} className="rounded border border-border-muted bg-surface-container px-2 py-1 text-body-sm">
                        {specialist}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <h3 className="mt-8 text-headline-sm">Critical Dependencies</h3>
              <div className="mt-4 space-y-3">
                {priority.dependencies.map((dependency) => (
                  <div key={dependency} className="flex items-center gap-3 rounded border border-outline-variant bg-surface p-4">
                    <CheckCircle2 className="h-5 w-5 text-status-moderate" />
                    {dependency}
                  </div>
                ))}
              </div>
            </Panel>

            <div className="flex flex-wrap gap-3 rounded-lg border border-outline-variant bg-surface-container-lowest p-5 shadow-panel">
              <Link href={`/reports?assessment=${assessmentId ?? "demo"}`} className="flex items-center gap-2 rounded border border-outline-variant px-4 py-2 text-headline-sm text-on-surface-variant">
                <Download className="h-4 w-4" />
                Structural Report
              </Link>
              <a href={`${API_BASE_URL}/assessments/${assessmentId ?? "demo"}/exports/geojson`} className="flex items-center gap-2 rounded border border-outline-variant px-4 py-2 text-headline-sm text-on-surface-variant">
                <Share2 className="h-4 w-4" />
                Engineering Data
              </a>
              <button onClick={() => setAssigned((value) => !value)} className="ml-auto flex items-center gap-2 rounded bg-primary px-6 py-2 text-headline-sm text-on-primary">
                <UserCheck className="h-4 w-4" />
                {assigned ? "Assigned" : "Mark as Assigned"}
              </button>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}

function EvidenceImage({ label, src }: { label: string; src: string }) {
  return (
    <div className="relative h-64 overflow-hidden rounded border border-outline-variant bg-surface-container">
      {/* eslint-disable-next-line @next/next/no-img-element -- backend artifact URLs are raw generated chips, not optimized public assets */}
      <img src={src} alt={label} className="h-full w-full object-cover" />
      <span className="absolute left-3 top-3 rounded bg-surface px-2 py-1 font-mono text-label-mono uppercase shadow-panel">{label}</span>
    </div>
  );
}

function EvidenceMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded border border-outline-variant bg-surface px-3 py-2">
      <span className="font-mono text-label-mono uppercase text-on-surface-variant">{label}</span>
      <span className="text-right font-mono text-label-mono uppercase text-primary">{value}</span>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-8 shadow-panel">
      <h2 className="mb-5 border-b border-border-muted pb-4 text-headline-md text-primary">{title}</h2>
      {children}
    </div>
  );
}

function Impact({ label, value, helper, danger = false, warning = false }: { label: string; value: string; helper: string; danger?: boolean; warning?: boolean }) {
  return (
    <div className="rounded border border-outline-variant bg-surface p-5">
      <div className="font-mono text-label-mono uppercase text-on-surface-variant">{label}</div>
      <div className={`mt-2 text-stat-value ${danger ? "text-status-destroyed" : warning ? "text-status-moderate" : "text-on-surface"}`}>{value}</div>
      <p className="text-body-sm">{helper}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border-muted py-4">
      <span className="font-mono text-label-mono uppercase text-on-surface-variant">{label}</span>
      <span className="text-stat-value">{value}</span>
    </div>
  );
}
