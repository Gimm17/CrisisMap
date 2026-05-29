"use client";

import { useEffect, useMemo } from "react";
import { GeoJSON, MapContainer, Marker, Polygon as LeafletPolygon, Polyline, TileLayer, Tooltip, ZoomControl, useMapEvents } from "react-leaflet";
import { divIcon } from "leaflet";
import type { Layer } from "leaflet";
import type { Polygon as GeoJsonPolygon, Position } from "geojson";

import type { BuildingFeatureCollection, DamageTier, ImageryMetadata, ImageryViewMode } from "@/lib/types";

const severityColors: Record<DamageTier, string> = {
  intact: "#22C55E",
  minor: "#EAB308",
  moderate: "#F59E0B",
  severe: "#EA580C",
  destroyed: "#DC2626"
};

type Props = {
  geojson: BuildingFeatureCollection;
  center?: [number, number];
  mode?: "workspace" | "dashboard";
  aoiGeoJson?: GeoJsonPolygon | null;
  draftPoints?: LatLngPoint[];
  drawingEnabled?: boolean;
  onDraftPointsChange?: (points: LatLngPoint[]) => void;
  onAoiChange?: (polygon: GeoJsonPolygon | null) => void;
  imageryMode?: ImageryViewMode;
  imageryMetadata?: ImageryMetadata | null;
};

type LatLngPoint = [number, number];

function latLngsToPolygon(points: LatLngPoint[]): GeoJsonPolygon | null {
  if (points.length < 3) return null;
  const ring: Position[] = points.map(([lat, lng]) => [lng, lat]);
  ring.push([points[0][1], points[0][0]]);
  return { type: "Polygon", coordinates: [ring] };
}

function polygonToLatLngs(polygon: GeoJsonPolygon | null | undefined): LatLngPoint[] {
  const positions = (polygon?.coordinates?.[0] ?? []).map((point) => [Number(point[1]), Number(point[0])] as LatLngPoint);
  const first = positions[0];
  const last = positions[positions.length - 1];
  if (first && last && first[0] === last[0] && first[1] === last[1]) {
    return positions.slice(0, -1);
  }
  return positions;
}

function AoiDrawingLayer({
  polygon,
  draftPoints = [],
  drawingEnabled = false,
  onDraftPointsChange,
  onAoiChange
}: {
  polygon?: GeoJsonPolygon | null;
  draftPoints?: LatLngPoint[];
  drawingEnabled?: boolean;
  onDraftPointsChange?: (points: LatLngPoint[]) => void;
  onAoiChange?: (polygon: GeoJsonPolygon | null) => void;
}) {
  const selectedPositions = useMemo(() => polygonToLatLngs(polygon), [polygon]);
  const previewPositions = draftPoints.length ? draftPoints : selectedPositions;
  const closedPreviewPositions = previewPositions.length >= 3 ? [...previewPositions, previewPositions[0]] : previewPositions;

  const map = useMapEvents({
    click(event) {
      if (!drawingEnabled) return;
      const next: LatLngPoint[] = [...draftPoints, [event.latlng.lat, event.latlng.lng]];
      onDraftPointsChange?.(next);
      const nextPolygon = latLngsToPolygon(next);
      onAoiChange?.(nextPolygon);
    },
    dblclick() {
      if (!drawingEnabled) return;
      onAoiChange?.(latLngsToPolygon(draftPoints));
    },
    contextmenu() {
      if (!drawingEnabled) return;
      onDraftPointsChange?.([]);
      onAoiChange?.(null);
    }
  });

  useEffect(() => {
    if (drawingEnabled) {
      map.doubleClickZoom.disable();
      return () => {
        map.doubleClickZoom.enable();
      };
    }
    map.doubleClickZoom.enable();
  }, [drawingEnabled, map]);

  return (
    <>
      {previewPositions.length >= 3 ? (
        <LeafletPolygon
          pathOptions={{ color: "#088395", fillColor: "#088395", fillOpacity: 0.16, opacity: 1, weight: 3, dashArray: "8 6" }}
          positions={closedPreviewPositions}
        />
      ) : null}
      {drawingEnabled && previewPositions.length >= 2 ? (
        <Polyline pathOptions={{ color: "#09637E", opacity: 1, weight: 3, dashArray: "4 6" }} positions={previewPositions} />
      ) : null}
      {previewPositions.map((position, index) => {
        const isLast = index === previewPositions.length - 1;
        return (
          <Marker
            key={`${position[0]}-${position[1]}-${index}`}
            position={position}
            icon={vertexIcon(index + 1, isLast)}
            interactive={false}
          >
            {isLast ? (
              <Tooltip direction="top" offset={[0, -14]} permanent>
                Last point
              </Tooltip>
            ) : null}
          </Marker>
        );
      })}
    </>
  );
}

function vertexIcon(label: number, isLast: boolean) {
  const background = isLast ? "#09637E" : "#088395";
  const ring = isLast ? "0 0 0 4px rgba(8, 131, 149, 0.22)" : "0 0 0 2px rgba(255,255,255,0.95)";
  return divIcon({
    className: "",
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    html: `<div style="display:flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:999px;background:${background};color:white;border:2px solid white;box-shadow:${ring};font:700 11px/1 JetBrains Mono, monospace;">${label}</div>`
  });
}

export default function LeafletDamageMap({
  geojson,
  center = [33.901, 35.518],
  mode = "dashboard",
  aoiGeoJson,
  draftPoints = [],
  drawingEnabled = false,
  onDraftPointsChange,
  onAoiChange,
  imageryMode = "damage",
  imageryMetadata = null
}: Props) {
  const localImageryReady = Boolean(
    imageryMetadata?.ready &&
      imageryMetadata.layers.before.status === "ready" &&
      imageryMetadata.layers.after.status === "ready" &&
      imageryMetadata.layers.before.tile_url_template &&
      imageryMetadata.layers.after.tile_url_template
  );
  const effectiveMode = localImageryReady ? imageryMode : "damage";
  const showDamage = effectiveMode === "damage";
  const showLocalImagery = localImageryReady;
  const showFallbackBasemap = !showLocalImagery;

  if (effectiveMode === "split" && showLocalImagery) {
    return (
      <div className="relative h-full w-full overflow-hidden bg-surface-container">
        <div className="grid h-full w-full grid-cols-2">
          <SplitMapPanel
            label="Before"
            tileUrl={imageryMetadata?.layers.before.tile_url_template ?? ""}
            center={center}
            aoiGeoJson={aoiGeoJson}
            draftPoints={draftPoints}
            drawingEnabled={drawingEnabled}
            onDraftPointsChange={onDraftPointsChange}
            onAoiChange={onAoiChange}
            imageryMetadata={imageryMetadata}
          />
          <SplitMapPanel
            label="After"
            tileUrl={imageryMetadata?.layers.after.tile_url_template ?? ""}
            center={center}
            aoiGeoJson={aoiGeoJson}
            draftPoints={draftPoints}
            drawingEnabled={drawingEnabled}
            onDraftPointsChange={onDraftPointsChange}
            onAoiChange={onAoiChange}
            imageryMetadata={imageryMetadata}
          />
        </div>
        <div className="pointer-events-none absolute bottom-0 left-1/2 top-0 z-[560] w-1 -translate-x-1/2 bg-white shadow-[0_0_0_1px_rgba(9,99,126,0.35)]" />
      </div>
    );
  }

  const singleImageryUrl =
    showLocalImagery && effectiveMode === "before"
      ? imageryMetadata?.layers.before.tile_url_template
      : imageryMetadata?.layers.after.tile_url_template;

  return (
    <div className="relative h-full w-full">
      <MapContainer center={center} zoom={14} minZoom={11} maxZoom={18} zoomControl={false} className="z-0">
        {showLocalImagery ? (
          <TileLayer
            attribution={imageryMetadata?.attribution ?? "Maxar Open Data"}
            maxZoom={imageryMetadata?.max_zoom ?? 18}
            minZoom={imageryMetadata?.min_zoom ?? 11}
            url={singleImageryUrl ?? ""}
          />
        ) : null}
        {showFallbackBasemap ? (
          <TileLayer
            attribution="Tiles &copy; Esri"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
        ) : null}
        {showFallbackBasemap || showDamage ? <TileLayer attribution="OpenStreetMap" opacity={0.25} url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /> : null}
        <ZoomControl position="topright" />
        {showDamage ? (
          <GeoJSON
            key={JSON.stringify(geojson.features.map((feature) => feature.properties.building_id))}
            data={geojson}
            style={(feature) => {
              const tier = feature?.properties?.damage_tier as DamageTier;
              const color = severityColors[tier] ?? severityColors.moderate;
              return {
                color,
                weight: 2,
                opacity: 1,
                fillColor: color,
                fillOpacity: mode === "workspace" ? 0.28 : 0.42
              };
            }}
            onEachFeature={(feature, layer: Layer) => {
              const props = feature.properties;
              layer.bindTooltip(`${props.name} - ${props.damage_score}/100`, { sticky: true });
            }}
          />
        ) : null}
        <AoiDrawingLayer
          polygon={aoiGeoJson}
          draftPoints={draftPoints}
          drawingEnabled={drawingEnabled}
          onDraftPointsChange={onDraftPointsChange}
          onAoiChange={onAoiChange}
        />
      </MapContainer>
      {showDamage ? <div className="pointer-events-none absolute inset-0 z-[400] map-grid-overlay opacity-30" /> : null}
      {!showLocalImagery && mode === "workspace" ? (
        <div className="absolute left-5 top-5 z-[520] rounded border border-status-minor/30 bg-white/95 px-3 py-2 text-body-sm text-on-surface-variant shadow-panel">
          Local imagery unavailable. Showing fallback basemap.
        </div>
      ) : null}
      {showDamage ? (
        <div className="absolute bottom-6 right-6 z-[500] rounded-xl border border-outline-variant bg-surface/95 p-4 shadow-panel">
        <h4 className="mb-3 border-b border-outline-variant pb-2 font-mono text-label-mono uppercase text-on-surface-variant">Damage Scale</h4>
        {[
          ["Destroyed", "bg-status-destroyed"],
          ["Severe Damage", "bg-status-severe"],
          ["Moderate Damage", "bg-status-moderate"],
          ["Minor Damage", "bg-status-minor"],
          ["Intact", "bg-status-intact"]
        ].map(([label, color]) => (
          <div key={label} className="mb-2 flex items-center gap-3 text-body-sm">
            <span className={`h-4 w-4 rounded-sm ${color}`} />
            {label}
          </div>
        ))}
        </div>
      ) : null}
    </div>
  );
}

function SplitMapPanel({
  label,
  tileUrl,
  center,
  aoiGeoJson,
  draftPoints,
  drawingEnabled,
  onDraftPointsChange,
  onAoiChange,
  imageryMetadata
}: {
  label: "Before" | "After";
  tileUrl: string;
  center: [number, number];
  aoiGeoJson?: GeoJsonPolygon | null;
  draftPoints: LatLngPoint[];
  drawingEnabled: boolean;
  onDraftPointsChange?: (points: LatLngPoint[]) => void;
  onAoiChange?: (polygon: GeoJsonPolygon | null) => void;
  imageryMetadata: ImageryMetadata | null;
}) {
  return (
    <div className="relative min-w-0 overflow-hidden border-outline-variant bg-surface-container">
      <MapContainer center={center} zoom={14} minZoom={11} maxZoom={18} zoomControl={false} className="z-0">
        <TileLayer
          attribution={imageryMetadata?.attribution ?? "Maxar Open Data"}
          maxZoom={imageryMetadata?.max_zoom ?? 18}
          minZoom={imageryMetadata?.min_zoom ?? 11}
          url={tileUrl}
        />
        <AoiDrawingLayer
          polygon={aoiGeoJson}
          draftPoints={draftPoints}
          drawingEnabled={drawingEnabled}
          onDraftPointsChange={onDraftPointsChange}
          onAoiChange={onAoiChange}
        />
        {label === "After" ? <ZoomControl position="topright" /> : null}
      </MapContainer>
      <div className="pointer-events-none absolute left-5 top-5 z-[520] rounded border border-outline-variant bg-white/95 px-3 py-1 font-mono text-label-mono uppercase text-primary shadow-panel">
        {label}
      </div>
    </div>
  );
}
