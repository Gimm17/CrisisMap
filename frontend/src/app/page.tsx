"use client";

import { useEffect, useState } from "react";
import type { ElementType } from "react";
import type { Polygon, Position } from "geojson";
import { BarChart3, Calendar, Check, Columns2, Crosshair, Image, LocateFixed, MapPin, PenLine, Play, Redo2, Satellite, Trash2, Undo2 } from "lucide-react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/AppShell";
import { DynamicDamageMap } from "@/components/map/DynamicDamageMap";
import { createAssessment, getAnalysisSettings, getDataSourceStatus, getImageryMetadata } from "@/lib/api";
import { demoGeoJson } from "@/lib/demo";
import { TOKENROUTER_MODELS } from "@/lib/settings";
import type { AnalysisSettings, AssessmentCreatePayload, DataSourceReadiness, DataSourceReadinessItem, ImageryMetadata, ImageryViewMode, TokenRouterModel } from "@/lib/types";

const fallbackSettings: AnalysisSettings = {
  model_profile: "damage",
  tokenrouter_model: "anthropic/claude-sonnet-4.6",
  confidence_threshold: 85,
  processing_priority: "standard",
  raw_imagery_retention_days: 90,
  scrub_metadata_on_export: false,
  auto_publish_destroyed_tags: true
};

const sourceDetails = {
  "OSM Buildings": "Building and infrastructure layers are read server-side from the local Beirut data registry when available.",
  "Before Imagery": "Pre-event Maxar imagery is registered as the structural baseline for the Beirut pipeline.",
  "After Imagery": "Post-event Maxar/OpenAerialMap imagery and Copernicus validation layers are available for damage assessment.",
  "Humanitarian Layers": "Local HDX healthsites and humanitarian layers are summarized for the AOI and passed into the reasoning/report pipeline.",
  "AI Model": "Image damage scoring stays server-side; TokenRouter only generates humanitarian reasoning and reports."
};

type SourceKey = keyof typeof sourceDetails;
type LatLngPoint = [number, number];

const DEFAULT_AOI: Polygon = {
  type: "Polygon",
  coordinates: [
    [
      [35.507, 33.895],
      [35.531, 33.895],
      [35.531, 33.909],
      [35.507, 33.909],
      [35.507, 33.895]
    ]
  ]
};

export default function WorkspacePage() {
  const [status, setStatus] = useState("Idle");
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [locationName, setLocationName] = useState("Beirut Port, Lebanon");
  const [eventDate, setEventDate] = useState("2020-08-04");
  const [preStart, setPreStart] = useState("2020-07-01");
  const [preEnd, setPreEnd] = useState("2020-08-03");
  const [postStart, setPostStart] = useState("2020-08-05");
  const [postEnd, setPostEnd] = useState("2020-08-15");
  const [settings, setSettings] = useState<AnalysisSettings>(fallbackSettings);
  const [drawMode, setDrawMode] = useState(false);
  const [aoiGeoJson, setAoiGeoJson] = useState<Polygon | null>(DEFAULT_AOI);
  const [draftPoints, setDraftPoints] = useState<LatLngPoint[]>(() => polygonToDraftPoints(DEFAULT_AOI));
  const [redoStack, setRedoStack] = useState<LatLngPoint[]>([]);
  const [aoiFeedback, setAoiFeedback] = useState("AOI ready");
  const [sourceStatus, setSourceStatus] = useState<DataSourceReadiness>({});
  const [imageryMetadata, setImageryMetadata] = useState<ImageryMetadata | null>(null);
  const [imageryMode, setImageryMode] = useState<ImageryViewMode>("damage");
  const [holdBefore, setHoldBefore] = useState(false);
  const [activeTool, setActiveTool] = useState("locate");
  const [toolMessage, setToolMessage] = useState("Map centered on Beirut Port AOI.");
  const [selectedSource, setSelectedSource] = useState<SourceKey>("OSM Buildings");
  const router = useRouter();
  const aoiStats = getAoiStats(draftPoints);
  const liveAoiInvalid = mode === "live" && !aoiStats.valid;
  const canUndo = draftPoints.length > 0;
  const canRedo = redoStack.length > 0;
  const imageryReady = Boolean(
    imageryMetadata?.ready &&
      imageryMetadata.layers.before.status === "ready" &&
      imageryMetadata.layers.after.status === "ready"
  );
  const effectiveImageryMode = holdBefore && imageryReady && imageryMode !== "split" ? "before" : imageryMode;

  function applyDraftPoints(points: LatLngPoint[], feedback: string, clearRedo = false) {
    setDraftPoints(points);
    setAoiGeoJson(draftPointsToPolygon(points));
    setAoiFeedback(feedback);
    if (clearRedo) setRedoStack([]);
  }

  function handleMapDraftChange(points: LatLngPoint[]) {
    applyDraftPoints(points, `Drawing point ${points.length}`, true);
  }

  function undoPoint() {
    if (!canUndo) return;
    const removed = draftPoints[draftPoints.length - 1];
    const next = draftPoints.slice(0, -1);
    setRedoStack((current) => [...current, removed]);
    applyDraftPoints(next, `Undo point ${draftPoints.length}`);
  }

  function redoPoint() {
    if (!canRedo) return;
    const restored = redoStack[redoStack.length - 1];
    const nextRedo = redoStack.slice(0, -1);
    const next = [...draftPoints, restored];
    setRedoStack(nextRedo);
    applyDraftPoints(next, `Redo point ${next.length}`);
  }

  function startDrawing() {
    if (!draftPoints.length && aoiGeoJson) {
      applyDraftPoints(polygonToDraftPoints(aoiGeoJson), "Drawing mode enabled");
    }
    setDrawMode(true);
    setActiveTool("draw");
    setToolMessage("Drawing mode enabled. Click the map to add AOI points. Use Undo/Redo from the panel.");
  }

  function toggleDrawing() {
    if (drawMode) {
      setDrawMode(false);
      setAoiFeedback(aoiStats.valid ? "AOI finalized" : "AOI draft paused");
      setToolMessage(aoiStats.valid ? "AOI polygon finalized for the next assessment." : "AOI draft paused. Add at least three points before running live assessment.");
      return;
    }
    startDrawing();
  }

  useEffect(() => {
    void getAnalysisSettings(fallbackSettings).then(setSettings);
    void getDataSourceStatus().then(setSourceStatus);
    void getImageryMetadata().then(setImageryMetadata);
  }, []);

  async function runAssessment() {
    const eventTime = new Date(eventDate).getTime();
    const preStartTime = new Date(preStart).getTime();
    const preEndTime = new Date(preEnd).getTime();
    const postStartTime = new Date(postStart).getTime();
    const postEndTime = new Date(postEnd).getTime();
    if ([eventTime, preStartTime, preEndTime, postStartTime, postEndTime].some(Number.isNaN)) {
      setStatus("Failed");
      setToolMessage("Date validation failed. Complete every temporal field before running.");
      return;
    }
    if (preStartTime > preEndTime || preEndTime >= eventTime || postStartTime <= eventTime || postStartTime > postEndTime) {
      setStatus("Failed");
      setToolMessage("Date validation failed. Before range must end before event date and after range must start after event date.");
      return;
    }
    if (mode === "live" && !aoiStats.valid) {
      setStatus("Failed");
      setToolMessage("Live assessment requires a valid AOI polygon. Draw at least three vertices before running.");
      return;
    }
    setStatus("Running");
    setToolMessage("Assessment request sent to the backend pipeline.");
    const selectedAoi = draftPointsToPolygon(draftPoints) ?? aoiGeoJson ?? DEFAULT_AOI;
    const payload: AssessmentCreatePayload = {
      mode,
      name: mode === "demo" ? "Beirut Port Assessment" : `${locationName} Live Assessment`,
      location_name: locationName,
      aoi_geojson: selectedAoi,
      event_date: eventDate,
      pre_date_start: preStart,
      pre_date_end: preEnd,
      post_date_start: postStart,
      post_date_end: postEnd,
      model_profile: settings.model_profile,
      processing_priority: settings.processing_priority,
      tokenrouter_model: settings.tokenrouter_model
    };
    try {
      const assessment = await createAssessment(payload);
      setStatus("Completed");
      setToolMessage(`Assessment ${assessment.assessment_id} completed with ${assessment.tokenrouter?.provider ?? "fallback"} reasoning.`);
      router.push(`/dashboard?assessment=${assessment.assessment_id}`);
    } catch (error) {
      setStatus(error instanceof Error ? "Failed" : "Failed");
      setToolMessage(error instanceof Error ? error.message : "Assessment failed.");
    }
  }

  return (
    <AppShell sidebar={false}>
      <div className="flex h-full">
        <aside className="hidden h-full w-panel-width shrink-0 flex-col border-r border-outline-variant bg-surface-container-lowest md:flex">
          <div className="border-b border-outline-variant bg-surface-container-low p-5">
            <div className="flex items-center gap-3">
              <span className={`h-2 w-2 rounded-full ${status === "Failed" ? "bg-status-destroyed" : status === "Completed" ? "bg-status-intact" : "bg-status-minor"}`} />
              <div>
                <h2 className="text-headline-sm">New Assessment</h2>
                <p className="text-body-sm text-on-surface-variant">Configure parameters for analysis</p>
              </div>
            </div>
            <div className="mt-5 flex rounded bg-surface-container-highest p-1 font-mono text-label-mono">
              <button onClick={() => setMode("demo")} className={`flex-1 rounded py-2 ${mode === "demo" ? "bg-surface-container-lowest shadow-sm" : "text-on-surface-variant"}`}>Demo (Beirut)</button>
              <button onClick={() => setMode("live")} className={`flex-1 rounded py-2 ${mode === "live" ? "bg-surface-container-lowest shadow-sm" : "text-on-surface-variant"}`}>Live Data</button>
            </div>
          </div>

          <div className="flex-1 space-y-7 overflow-y-auto p-5">
            <section>
              <h3 className="mb-3 font-mono text-label-mono uppercase text-on-surface-variant">Area of Interest</h3>
              <label className="relative block">
                <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
                <input
                  className="w-full rounded border border-outline-variant bg-surface py-2 pl-9 pr-3 text-body-sm"
                  value={locationName}
                  onChange={(event) => setLocationName(event.target.value)}
                />
              </label>
              <button
                onClick={toggleDrawing}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded border border-outline-variant bg-white px-4 py-2 text-body-sm"
              >
                <PenLine className="h-4 w-4" />
                {drawMode ? "Finish Drawing" : "Draw Area"}
              </button>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <AoiControlButton
                  icon={Undo2}
                  label="Undo"
                  disabled={!canUndo}
                  title={canUndo ? "Remove last AOI point" : "No AOI point to undo"}
                  onClick={undoPoint}
                />
                <AoiControlButton
                  icon={Redo2}
                  label="Redo"
                  disabled={!canRedo}
                  title={canRedo ? "Restore last undone AOI point" : "No AOI point to redo"}
                  onClick={redoPoint}
                />
                <button
                  onClick={() => {
                    const polygon = draftPointsToPolygon(draftPoints);
                    if (polygon) setAoiGeoJson(polygon);
                    setDrawMode(false);
                    setAoiFeedback("AOI finalized");
                    setToolMessage("AOI polygon finalized for the next assessment.");
                  }}
                  disabled={!aoiStats.valid}
                  title={aoiStats.valid ? "Use this AOI polygon" : "Draw at least three points first"}
                  className="flex items-center justify-center gap-2 rounded border border-outline-variant bg-surface px-3 py-2 text-body-sm disabled:opacity-50"
                >
                  <Check className="h-4 w-4" />
                  Use Area
                </button>
                <button
                  onClick={() => {
                    setAoiGeoJson(null);
                    setDraftPoints([]);
                    setRedoStack([]);
                    setDrawMode(false);
                    setAoiFeedback("AOI cleared");
                    setToolMessage("AOI cleared. Live mode will stay blocked until a new polygon is drawn.");
                  }}
                  className="flex items-center justify-center gap-2 rounded border border-outline-variant bg-surface px-3 py-2 text-body-sm"
                >
                  <Trash2 className="h-4 w-4" />
                  Clear Area
                </button>
              </div>
              <div className="mt-3 rounded border border-outline-variant bg-surface px-3 py-2 font-mono text-label-mono">
                <div className="flex justify-between">
                  <span>AOI Status</span>
                  <span className={aoiStats.valid ? "text-status-intact" : "text-status-destroyed"}>{aoiStats.valid ? "Valid" : "Invalid"}</span>
                </div>
                <div className="mt-2 flex justify-between text-on-surface-variant">
                  <span>{aoiStats.vertices} vertices</span>
                  <span>{aoiStats.areaKm2.toFixed(3)} km2</span>
                </div>
                <div className="mt-2 border-t border-outline-variant pt-2 text-on-surface-variant">{aoiFeedback}</div>
              </div>
            </section>

            <section>
              <h3 className="mb-3 font-mono text-label-mono uppercase text-on-surface-variant">Temporal Parameters</h3>
              <DateInput label="Event Date (Anchor)" value={eventDate} onChange={setEventDate} />
              <div className="mt-3 grid grid-cols-2 gap-3">
                <DateInput label="Before Image Range" value={preStart} onChange={setPreStart} second={preEnd} onSecondChange={setPreEnd} />
                <DateInput label="After Image Range" value={postStart} onChange={setPostStart} second={postEnd} onSecondChange={setPostEnd} />
              </div>
            </section>

            <section>
              <h3 className="mb-3 font-mono text-label-mono uppercase text-on-surface-variant">AI Routing</h3>
              <select
                className="w-full rounded border border-outline-variant bg-surface px-3 py-2 text-body-sm"
                value={settings.tokenrouter_model}
                onChange={(event) => setSettings((current) => ({ ...current, tokenrouter_model: event.target.value as TokenRouterModel }))}
              >
                {TOKENROUTER_MODELS.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </section>

            <section>
              <h3 className="mb-3 font-mono text-label-mono uppercase text-on-surface-variant">Data Sources</h3>
              <div className="space-y-2 rounded border border-outline-variant bg-surface p-3">
                <SourceRow icon={MapPin} label="OSM Buildings" status={statusLabel(sourceStatus.osm)} active={selectedSource === "OSM Buildings"} onClick={() => setSelectedSource("OSM Buildings")} />
                <SourceRow icon={Satellite} label="Before Imagery" status={statusLabel(sourceStatus.imagery?.maxar_pre)} active={selectedSource === "Before Imagery"} onClick={() => setSelectedSource("Before Imagery")} />
                <SourceRow icon={Image} label="After Imagery" status={statusLabel(sourceStatus.imagery?.maxar_post)} active={selectedSource === "After Imagery"} onClick={() => setSelectedSource("After Imagery")} />
                <SourceRow icon={BarChart3} label="Humanitarian Layers" status={statusLabel(sourceStatus.hdx)} active={selectedSource === "Humanitarian Layers"} onClick={() => setSelectedSource("Humanitarian Layers")} />
                <SourceRow icon={BarChart3} label={`AI Model (${settings.model_profile})`} status={sourceStatus.tokenrouter?.status === "configured" ? "Ready" : "Fallback"} active={selectedSource === "AI Model"} onClick={() => setSelectedSource("AI Model")} />
                <div className="rounded border border-outline-variant bg-surface-container-lowest p-3 text-body-sm text-on-surface-variant">
                  {sourceDetails[selectedSource]}
                </div>
              </div>
            </section>
          </div>

          <div className="border-t border-outline-variant bg-surface p-5">
            <div className="mb-3 flex justify-between text-body-sm">
              <span className="text-on-surface-variant">Job Status:</span>
              <span className="font-mono text-label-mono">{status}</span>
            </div>
            <button
              onClick={runAssessment}
              disabled={status === "Running" || liveAoiInvalid}
              title={liveAoiInvalid ? "Live assessment requires a valid AOI polygon" : status === "Running" ? "Assessment is running" : "Run assessment"}
              className="flex w-full items-center justify-center gap-2 rounded bg-[#088395] px-4 py-3 text-headline-sm text-white disabled:opacity-60"
            >
              <Play className="h-5 w-5" />
              Run Assessment
            </button>
          </div>
        </aside>

        <section className="relative min-w-0 flex-1">
          <DynamicDamageMap
            geojson={demoGeoJson}
            mode="workspace"
            aoiGeoJson={aoiGeoJson}
            draftPoints={draftPoints}
            drawingEnabled={drawMode}
            onDraftPointsChange={handleMapDraftChange}
            onAoiChange={setAoiGeoJson}
            imageryMode={effectiveImageryMode}
            imageryMetadata={imageryMetadata}
          />
          <ImageryModeControl
            mode={imageryMode}
            ready={imageryReady}
            holding={holdBefore}
            onModeChange={(nextMode) => {
              setImageryMode(nextMode);
              if (nextMode === "split") setHoldBefore(false);
              setToolMessage(
                nextMode === "damage"
                  ? "Damage layer shown over post-event imagery."
                  : nextMode === "split"
                    ? "Independent split comparison enabled: control before and after maps separately."
                    : `${nextMode === "before" ? "Before" : "After"} imagery layer enabled.`
              );
            }}
            onHoldChange={setHoldBefore}
          />
          <div className="absolute left-1/2 top-1/3 z-[500] hidden -translate-x-1/2 rounded border border-primary bg-surface/80 px-2 py-1 font-mono text-label-mono md:block">
            {drawMode ? "Click map to add points. Use Undo/Redo from panel." : aoiStats.valid ? "AOI: Ready" : "AOI: Not selected"}
          </div>
          {activeTool === "crosshair" ? (
            <div className="pointer-events-none absolute inset-0 z-[480] hidden md:block">
              <div className="absolute left-1/2 top-0 h-full w-px bg-primary/60" />
              <div className="absolute left-0 top-1/2 h-px w-full bg-primary/60" />
            </div>
          ) : null}
          <div className="absolute right-5 top-5 z-[500] flex flex-col overflow-hidden rounded border border-outline-variant bg-white shadow-panel">
            <ToolButton
              icon={LocateFixed}
              active={activeTool === "locate"}
              onClick={() => {
                setActiveTool("locate");
                setLocationName("Beirut Port, Lebanon");
                setToolMessage("Map recentered to Beirut Port, Lebanon.");
              }}
              label="Locate"
            />
            <ToolButton
              icon={Crosshair}
              active={activeTool === "crosshair"}
              onClick={() => {
                setActiveTool("crosshair");
                setToolMessage("Crosshair inspection overlay enabled.");
              }}
              label="Crosshair"
            />
            <ToolButton
              icon={PenLine}
              active={activeTool === "draw"}
              onClick={() => {
                startDrawing();
              }}
              label="Draw"
            />
          </div>
          <div className="absolute left-5 bottom-6 z-[500] hidden max-w-sm rounded border border-outline-variant bg-white/95 p-4 shadow-panel md:block">
            <p className="font-mono text-label-mono uppercase text-primary">Map Tool</p>
            <p className="mt-1 text-body-sm text-on-surface-variant">{toolMessage}</p>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function ImageryModeControl({
  mode,
  ready,
  holding,
  onModeChange,
  onHoldChange
}: {
  mode: ImageryViewMode;
  ready: boolean;
  holding: boolean;
  onModeChange: (mode: ImageryViewMode) => void;
  onHoldChange: (holding: boolean) => void;
}) {
  const modes: Array<{ value: ImageryViewMode; label: string }> = [
    { value: "damage", label: "Damage" },
    { value: "after", label: "After" },
    { value: "before", label: "Before" },
    { value: "split", label: "Split" }
  ];
  return (
    <div className="absolute left-1/2 top-5 z-[650] hidden -translate-x-1/2 items-center gap-2 rounded-lg border border-outline-variant bg-white/95 p-2 shadow-panel md:flex">
      <div className="flex rounded bg-surface-container-highest p-1 font-mono text-label-mono">
        {modes.map((item) => {
          const disabled = item.value !== "damage" && !ready;
          return (
            <button
              key={item.value}
              className={`rounded px-3 py-2 ${mode === item.value ? "bg-primary text-on-primary shadow-sm" : "text-on-surface-variant hover:bg-surface"} disabled:opacity-45`}
              disabled={disabled}
              onClick={() => onModeChange(item.value)}
              title={disabled ? "Local imagery unavailable" : `Show ${item.label}`}
              type="button"
            >
              {item.label}
            </button>
          );
        })}
      </div>
      <button
        className={`flex items-center gap-2 rounded border border-outline-variant px-3 py-2 font-mono text-label-mono uppercase ${holding && mode !== "split" ? "bg-primary text-on-primary" : "bg-surface text-primary"} disabled:opacity-45`}
        disabled={!ready || mode === "split"}
        onKeyDown={(event) => {
          if (event.key === " " || event.key === "Enter") {
            event.preventDefault();
            onHoldChange(true);
          }
        }}
        onKeyUp={(event) => {
          if (event.key === " " || event.key === "Enter") {
            event.preventDefault();
            onHoldChange(false);
          }
        }}
        onPointerCancel={() => onHoldChange(false)}
        onPointerDown={() => onHoldChange(true)}
        onPointerLeave={() => onHoldChange(false)}
        onPointerUp={() => onHoldChange(false)}
        title={!ready ? "Local imagery unavailable" : mode === "split" ? "Before and after are already visible in split mode" : "Hold to temporarily show before imagery"}
        type="button"
      >
        <Columns2 className="h-4 w-4" />
        Hold Before
      </button>
    </div>
  );
}

function polygonToDraftPoints(polygon: Polygon | null): LatLngPoint[] {
  const points = (polygon?.coordinates?.[0] ?? []).map((point) => [Number(point[1]), Number(point[0])] as LatLngPoint);
  const first = points[0];
  const last = points[points.length - 1];
  if (first && last && first[0] === last[0] && first[1] === last[1]) {
    return points.slice(0, -1);
  }
  return points;
}

function draftPointsToPolygon(points: LatLngPoint[]): Polygon | null {
  if (points.length < 3) return null;
  const ring: Position[] = points.map(([lat, lng]) => [lng, lat]);
  ring.push([points[0][1], points[0][0]]);
  return { type: "Polygon", coordinates: [ring] };
}

function getAoiStats(points: LatLngPoint[]) {
  const vertices = points.length;
  if (vertices < 3) return { valid: false, vertices, areaKm2: 0 };
  const ring = [...points, points[0]];
  const meanLat = ring.reduce((sum, point) => sum + Number(point[0]), 0) / ring.length;
  const metersPerLon = 111320 * Math.cos((meanLat * Math.PI) / 180);
  const metersPerLat = 110540;
  const [originLat, originLng] = ring[0];
  const projectedPoints = ring.map(([lat, lng]) => [(Number(lng) - Number(originLng)) * metersPerLon, (Number(lat) - Number(originLat)) * metersPerLat]);
  const areaM2 = projectedPoints.reduce((area, point, index) => {
    const next = projectedPoints[(index + 1) % projectedPoints.length];
    return area + point[0] * next[1] - next[0] * point[1];
  }, 0);
  return { valid: Math.abs(areaM2) > 0, vertices, areaKm2: Math.abs(areaM2) / 2 / 1_000_000 };
}

function statusLabel(item?: DataSourceReadinessItem): string {
  if (!item?.status) return "Fallback";
  if (item.status === "ready" || item.status === "configured") return "Ready";
  if (item.status === "warning") return "Warning";
  if (item.status === "needs_credentials") return "Needs Credentials";
  if (item.status === "missing") return "Missing";
  return "Fallback";
}

function DateInput({ label, value, second, onChange, onSecondChange }: { label: string; value: string; second?: string; onChange: (value: string) => void; onSecondChange?: (value: string) => void }) {
  return (
    <label className="block text-body-sm text-on-surface-variant">
      {label}
      <span className="relative mt-1 block">
        <input className="w-full rounded border border-outline-variant bg-surface p-2 text-body-sm text-on-surface" type="date" value={value} onChange={(event) => onChange(event.target.value)} />
        <Calendar className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
      </span>
      {second && onSecondChange ? (
        <input className="mt-2 w-full rounded border border-outline-variant bg-surface p-2 text-body-sm text-on-surface" type="date" value={second} onChange={(event) => onSecondChange(event.target.value)} />
      ) : null}
    </label>
  );
}

function AoiControlButton({
  icon: Icon,
  label,
  disabled,
  title,
  onClick
}: {
  icon: ElementType;
  label: string;
  disabled: boolean;
  title: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="flex items-center justify-center gap-2 rounded border border-outline-variant bg-surface px-3 py-2 text-body-sm disabled:opacity-50"
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

function SourceRow({ icon: Icon, label, status, active, onClick }: { icon: ElementType; label: string; status: string; active: boolean; onClick: () => void }) {
  const healthy = status === "Ready";
  const warning = status === "Fallback" || status === "Warning" || status === "Needs Credentials";
  return (
    <button onClick={onClick} className={`flex w-full items-center justify-between rounded px-2 py-1 text-left ${active ? "bg-surface-container-high" : "hover:bg-surface-container-low"}`}>
      <span className="flex items-center gap-2 text-body-sm">
        <Icon className="h-4 w-4 text-primary" />
        {label}
      </span>
      <span className={`rounded px-2 py-0.5 font-mono text-label-mono ${healthy ? "bg-status-intact/20 text-status-intact" : warning ? "bg-status-minor/20 text-status-minor" : "bg-status-destroyed/10 text-status-destroyed"}`}>{status}</span>
    </button>
  );
}

function ToolButton({ icon: Icon, active, onClick, label }: { icon: ElementType; active: boolean; onClick: () => void; label: string }) {
  return (
    <button aria-label={label} onClick={onClick} className={`flex h-12 w-12 items-center justify-center text-primary hover:bg-surface-container ${active ? "bg-surface-container" : ""}`}>
      <Icon className="h-5 w-5" />
    </button>
  );
}
