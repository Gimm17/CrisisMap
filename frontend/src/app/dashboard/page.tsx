"use client";

import { useEffect, useMemo, useState } from "react";
import type { ElementType } from "react";
import Link from "next/link";
import { Building2, ChevronDown, Factory, Group, Hospital, Plus, Power, Route, Users, Zap } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { DynamicDamageMap } from "@/components/map/DynamicDamageMap";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatCard } from "@/components/ui/StatCard";
import { getAssessment, getBuildingsGeoJson, getPriorities } from "@/lib/api";
import { demoGeoJson } from "@/lib/demo";
import { formatNumber } from "@/lib/format";
import type { Assessment, BuildingFeatureCollection, PriorityBuilding } from "@/lib/types";

const infrastructureTypes = ["All Types", "Medical Facility", "Utility Infrastructure", "Logistics Hub", "Industrial Storage"];
const severityThresholds = { any: 0, severe: 61, critical: 80 };

type OverlayKey = "buildings" | "hospitals" | "roads" | "utilities" | "population";

export default function DashboardPage() {
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [geojson, setGeojson] = useState<BuildingFeatureCollection>(demoGeoJson);
  const [priorities, setPriorities] = useState<PriorityBuilding[]>([]);
  const [typeFilter, setTypeFilter] = useState("All Types");
  const [severityFilter, setSeverityFilter] = useState<"any" | "severe" | "critical">("severe");
  const [showAllPriorities, setShowAllPriorities] = useState(false);
  const [overlays, setOverlays] = useState<Record<OverlayKey, boolean>>({
    buildings: true,
    hospitals: false,
    roads: false,
    utilities: false,
    population: false
  });

  useEffect(() => {
    setAssessmentId(new URLSearchParams(window.location.search).get("assessment") ?? "demo");
  }, []);

  useEffect(() => {
    if (!assessmentId) return;
    let active = true;
    const id = assessmentId;
    async function loadAssessmentData() {
      const [nextAssessment, nextGeojson, nextPriorities] = await Promise.all([
        getAssessment(id),
        getBuildingsGeoJson(id),
        getPriorities(id)
      ]);
      if (!active) return;
      setAssessment(nextAssessment);
      setGeojson(nextGeojson);
      setPriorities(nextPriorities);
    }
    void loadAssessmentData();
    return () => {
      active = false;
    };
  }, [assessmentId]);

  const summary = assessment?.summary;
  const validationMetrics = assessment?.pipeline?.validation as
    | { metrics?: { macro_f1?: number; matched_buildings?: number } }
    | undefined;
  const filteredPriorities = useMemo(() => {
    const minimum = severityThresholds[severityFilter];
    return priorities.filter((priority) => {
      const typeMatch = typeFilter === "All Types" || priority.infrastructure_type === typeFilter;
      return typeMatch && priority.damage_score >= minimum;
    });
  }, [priorities, severityFilter, typeFilter]);

  const filteredGeoJson = useMemo<BuildingFeatureCollection>(() => {
    if (!overlays.buildings) return { ...geojson, features: [] };
    const minimum = severityThresholds[severityFilter];
    return {
      ...geojson,
      features: geojson.features.filter((feature) => {
        const typeMatch = typeFilter === "All Types" || feature.properties.infrastructure_type === typeFilter;
        return typeMatch && feature.properties.damage_score >= minimum;
      })
    };
  }, [geojson, overlays.buildings, severityFilter, typeFilter]);

  function resetFilters() {
    setTypeFilter("All Types");
    setSeverityFilter("severe");
    setShowAllPriorities(false);
  }

  function toggleOverlay(key: OverlayKey) {
    setOverlays((current) => ({ ...current, [key]: !current[key] }));
  }

  const visiblePriorities = showAllPriorities ? filteredPriorities : filteredPriorities.slice(0, 3);

  return (
    <AppShell>
      <div className="flex h-full">
        <section className="relative min-w-0 flex-1">
          <DynamicDamageMap geojson={filteredGeoJson} />
          <MapLayerOverlays overlays={overlays} />
          <div className="pointer-events-none absolute left-5 right-5 top-5 z-[500] hidden grid-cols-4 gap-4 xl:grid">
            <StatCard icon={Building2} label="Buildings Assessed" value={formatNumber(summary?.buildings_assessed ?? 1420)} />
            <StatCard icon={Zap} label="Severe/Destroyed" value={`${summary?.severe_or_destroyed ?? 84}`} helper="structures" tone="danger" />
            <StatCard icon={Power} label="Critical Infra" value={`${summary?.critical_infrastructure_affected ?? 12}`} helper="affected" tone="warning" />
            <StatCard icon={Users} label="Est. Pop Impact" value={`~${Math.round((summary?.estimated_population_impact ?? 155000) / 1000)}k`} />
          </div>
        </section>

        <aside className="hidden h-full w-panel-width shrink-0 overflow-y-auto border-l border-outline-variant bg-surface p-6 lg:block">
          <div className="border-b border-outline-variant pb-6">
            <h1 className="text-headline-md font-bold">Results Dashboard</h1>
            <p className="mt-1 text-body-sm text-on-surface-variant">{assessment?.location_name ?? "Beirut Port Assessment Region"}</p>
            <p className="mt-2 font-mono text-label-mono text-on-surface-variant">
              AI: {assessment?.tokenrouter?.model ?? "pending"} / {assessment?.tokenrouter?.provider ?? "pending"}
            </p>
            <p className="mt-1 font-mono text-label-mono text-on-surface-variant">
              Pipeline: {String(assessment?.pipeline?.method ?? "pending")}
            </p>
            <p className="mt-1 font-mono text-label-mono text-on-surface-variant">
              Validation: F1 {typeof validationMetrics?.metrics?.macro_f1 === "number" ? validationMetrics.metrics.macro_f1.toFixed(3) : "n/a"} /{" "}
              {validationMetrics?.metrics?.matched_buildings ?? 0} matched
            </p>
          </div>

          <section className="mt-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-mono text-label-mono uppercase text-primary">Data Filters</h2>
              <button onClick={resetFilters} className="font-mono text-label-mono text-primary underline">Reset</button>
            </div>
            <label className="block text-body-sm text-on-surface-variant">
              Infrastructure Type
              <span className="relative mt-1 block">
                <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} className="w-full appearance-none rounded-lg border border-outline-variant bg-surface px-3 py-2 text-body-sm text-on-surface">
                  {infrastructureTypes.map((type) => (
                    <option key={type}>{type}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
              </span>
            </label>
            <div className="mt-5">
              <p className="mb-1 text-body-sm text-on-surface-variant">Minimum Severity</p>
              <div className="grid grid-cols-3 rounded bg-surface-container-highest p-1">
                <SeverityButton label="Any" active={severityFilter === "any"} onClick={() => setSeverityFilter("any")} />
                <SeverityButton label="Severe+" active={severityFilter === "severe"} onClick={() => setSeverityFilter("severe")} />
                <SeverityButton label="Critical" active={severityFilter === "critical"} onClick={() => setSeverityFilter("critical")} />
              </div>
            </div>
          </section>

          <section className="mt-8">
            <h2 className="mb-3 font-mono text-label-mono uppercase text-primary">Active Overlays</h2>
            <div className="overflow-hidden rounded-lg border border-outline-variant">
              <OverlayRow icon={Building2} label="Building Footprints" enabled={overlays.buildings} onClick={() => toggleOverlay("buildings")} />
              <OverlayRow icon={Hospital} label="Medical Facilities" enabled={overlays.hospitals} onClick={() => toggleOverlay("hospitals")} />
              <OverlayRow icon={Route} label="Road Network Status" enabled={overlays.roads} onClick={() => toggleOverlay("roads")} />
              <OverlayRow icon={Power} label="Water & Power Grid" enabled={overlays.utilities} onClick={() => toggleOverlay("utilities")} />
              <OverlayRow icon={Group} label="Population Density Heatmap" enabled={overlays.population} onClick={() => toggleOverlay("population")} />
            </div>
          </section>

          <section className="mt-8">
            <div className="mb-3 flex justify-between">
              <h2 className="text-headline-sm font-bold">Priority Reconstruction</h2>
              <span className="font-mono text-label-mono text-outline">{showAllPriorities ? `${filteredPriorities.length} items` : "Top 3"}</span>
            </div>
            <div className="space-y-3">
              {visiblePriorities.map((priority) => (
                <Link
                  key={priority.building_id}
                  href={`/priority/${priority.building_id}?assessment=${assessmentId ?? "demo"}`}
                  className="relative block overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest p-4 shadow-sm hover:border-primary"
                >
                  <div className={`absolute bottom-0 left-0 top-0 w-1 ${priority.rank === 1 ? "bg-status-destroyed" : "bg-status-severe"}`} />
                  <div className="flex items-start justify-between gap-3 pl-3">
                    <div>
                      <p className="text-headline-md text-status-severe">#{priority.rank}</p>
                      <h3 className="font-semibold">{priority.name}</h3>
                      <p className="mt-1 flex items-center gap-1 text-body-sm text-on-surface-variant">
                        {priority.infrastructure_type.includes("Medical") ? <Hospital className="h-4 w-4" /> : <Factory className="h-4 w-4" />}
                        {priority.infrastructure_type}
                      </p>
                    </div>
                    <div className="text-right">
                      <SeverityBadge label={priority.status} />
                      <p className="mt-2 font-mono text-label-mono text-status-severe">Score: {priority.damage_score}</p>
                    </div>
                  </div>
                </Link>
              ))}
              {!visiblePriorities.length ? (
                <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-4 text-body-sm text-on-surface-variant">
                  No priorities match the current filters.
                </div>
              ) : null}
            </div>
            <button onClick={() => setShowAllPriorities((value) => !value)} className="mt-4 flex w-full items-center justify-center gap-1 rounded py-2 font-mono text-label-mono uppercase text-primary hover:bg-surface-container-high">
              {showAllPriorities ? "Collapse List" : "View Full List"}
              <Plus className={`h-4 w-4 ${showAllPriorities ? "" : "rotate-45"}`} />
            </button>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}

function SeverityButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`rounded py-1 text-body-sm ${active ? "bg-surface font-semibold shadow-sm" : "text-on-surface-variant"}`}>
      {label}
    </button>
  );
}

function OverlayRow({ icon: Icon, label, enabled = false, onClick }: { icon: ElementType; label: string; enabled?: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex w-full items-center justify-between border-b border-outline-variant px-4 py-3 text-left last:border-b-0">
      <span className="flex items-center gap-3 text-body-md">
        <Icon className={`h-5 w-5 ${enabled ? "text-primary" : "text-outline"}`} />
        {label}
      </span>
      <span className={`flex h-7 w-12 items-center rounded-full p-1 ${enabled ? "justify-end bg-primary" : "justify-start bg-outline-variant"}`}>
        <span className="h-5 w-5 rounded-full bg-white" />
      </span>
    </button>
  );
}

function MapLayerOverlays({ overlays }: { overlays: Record<OverlayKey, boolean> }) {
  return (
    <div className="pointer-events-none absolute inset-0 z-[450]">
      {overlays.roads ? (
        <div data-layer="roads" className="absolute left-[30%] top-[57%] h-2 w-[38%] rotate-[-8deg] rounded-full bg-status-minor/80 shadow-[0_0_0_4px_rgba(234,179,8,0.2)]" />
      ) : null}
      {overlays.utilities ? (
        <>
          <MapMarker label="Power" layer="utilities" className="left-[58%] top-[35%]" tone="bg-status-severe text-white" />
          <div data-layer="utilities" className="absolute left-[56%] top-[41%] h-24 w-px rotate-[32deg] bg-status-severe/80" />
        </>
      ) : null}
      {overlays.population ? (
        <div data-layer="population" className="absolute left-[36%] top-[34%] h-72 w-72 rounded-full bg-status-destroyed/20 blur-2xl" />
      ) : null}
    </div>
  );
}

function MapMarker({ label, layer, className, tone }: { label: string; layer: string; className: string; tone: string }) {
  return (
    <div data-layer={layer} className={`absolute rounded px-2 py-1 font-mono text-label-mono uppercase shadow-panel ${className} ${tone}`}>
      {label}
    </div>
  );
}
