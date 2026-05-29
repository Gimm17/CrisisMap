"use client";

import dynamic from "next/dynamic";
import type { Polygon } from "geojson";

import type { BuildingFeatureCollection, ImageryMetadata, ImageryViewMode } from "@/lib/types";

type LatLngPoint = [number, number];

const LeafletDamageMap = dynamic(() => import("./LeafletDamageMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-surface-container" />
});

export function DynamicDamageMap({
  geojson,
  mode = "dashboard",
  aoiGeoJson,
  draftPoints = [],
  drawingEnabled = false,
  onDraftPointsChange,
  onAoiChange,
  imageryMode = "damage",
  imageryMetadata = null
}: {
  geojson: BuildingFeatureCollection;
  mode?: "workspace" | "dashboard";
  aoiGeoJson?: Polygon | null;
  draftPoints?: LatLngPoint[];
  drawingEnabled?: boolean;
  onDraftPointsChange?: (points: LatLngPoint[]) => void;
  onAoiChange?: (polygon: Polygon | null) => void;
  imageryMode?: ImageryViewMode;
  imageryMetadata?: ImageryMetadata | null;
}) {
  return (
    <LeafletDamageMap
      geojson={geojson}
      mode={mode}
      aoiGeoJson={aoiGeoJson}
      draftPoints={draftPoints}
      drawingEnabled={drawingEnabled}
      onDraftPointsChange={onDraftPointsChange}
      onAoiChange={onAoiChange}
      imageryMode={imageryMode}
      imageryMetadata={imageryMetadata}
    />
  );
}
