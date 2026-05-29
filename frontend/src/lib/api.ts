import { demoAssessment, demoGeoJson, demoPriorities, demoReport } from "./demo";
import type {
  AnalysisSettings,
  ApiEnvelope,
  Assessment,
  AssessmentArtifacts,
  AssessmentCreatePayload,
  AssessmentReport,
  BuildingFeatureCollection,
  DataSourceReadiness,
  ImageryMetadata,
  PriorityBuilding
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function getEnvelope<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = (await response.json()) as ApiEnvelope<T>;
    return payload.data;
  } catch {
    return fallback;
  }
}

export async function createAssessment(payload: AssessmentCreatePayload = {}): Promise<Assessment> {
  try {
    const response = await fetch(`${API_BASE_URL}/assessments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "demo", name: "Beirut Port Assessment", ...payload })
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    const body = (await response.json()) as ApiEnvelope<Assessment>;
    return body.data;
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("HTTP")) throw error;
    return demoAssessment;
  }
}

export function listAssessments(): Promise<Assessment[]> {
  return getEnvelope<Assessment[]>("/assessments", [demoAssessment]);
}

export function getAssessment(id = "demo"): Promise<Assessment> {
  return getEnvelope<Assessment>(`/assessments/${id}`, demoAssessment);
}

export function getPriorities(id = "demo"): Promise<PriorityBuilding[]> {
  return getEnvelope<PriorityBuilding[]>(`/assessments/${id}/priorities`, demoPriorities);
}

export async function getBuildingsGeoJson(id = "demo"): Promise<BuildingFeatureCollection> {
  try {
    const response = await fetch(`${API_BASE_URL}/assessments/${id}/buildings.geojson`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return (await response.json()) as BuildingFeatureCollection;
  } catch {
    return demoGeoJson;
  }
}

export function getReport(id = "demo"): Promise<AssessmentReport> {
  return getEnvelope<AssessmentReport>(`/assessments/${id}/report`, demoReport);
}

export function getAssessmentArtifacts(id = "demo"): Promise<AssessmentArtifacts> {
  return getEnvelope<AssessmentArtifacts>(`/assessments/${id}/artifacts`, {});
}

export function getAssessmentQuality(id = "demo"): Promise<Record<string, unknown>> {
  return getEnvelope<Record<string, unknown>>(`/assessments/${id}/quality`, {});
}

export function getBuildingChipUrl(assessmentId: string, buildingId: string, kind: "pre" | "post"): string {
  return `${API_BASE_URL}/assessments/${assessmentId}/artifacts/chips/${buildingId}/${kind}.png`;
}

export async function getImageryMetadata(): Promise<ImageryMetadata> {
  const fallback: ImageryMetadata = {
    ready: false,
    tile_size: 256,
    min_zoom: 11,
    max_zoom: 18,
    default_bounds: null,
    attribution: "Local imagery unavailable",
    layers: {
      before: {
        kind: "before",
        label: "Before",
        date_label: "2020-07-31",
        status: "missing",
        tile_url_template: ""
      },
      after: {
        kind: "after",
        label: "After",
        date_label: "2020-08-05",
        status: "missing",
        tile_url_template: ""
      }
    }
  };
  const metadata = await getEnvelope<ImageryMetadata>("/imagery/beirut/metadata", fallback);
  return {
    ...metadata,
    layers: {
      before: {
        ...metadata.layers.before,
        tile_url_template: absolutizeApiPath(metadata.layers.before.tile_url_template)
      },
      after: {
        ...metadata.layers.after,
        tile_url_template: absolutizeApiPath(metadata.layers.after.tile_url_template)
      }
    }
  };
}

export function getDataSourceStatus(): Promise<DataSourceReadiness> {
  return getEnvelope<DataSourceReadiness>("/data-sources/status", {});
}

export function getAnalysisSettings(fallback: AnalysisSettings): Promise<AnalysisSettings> {
  return getEnvelope<AnalysisSettings>("/settings/analysis", fallback);
}

export async function updateAnalysisSettings(settings: AnalysisSettings): Promise<AnalysisSettings> {
  const response = await fetch(`${API_BASE_URL}/settings/analysis`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings)
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
  const payload = (await response.json()) as ApiEnvelope<AnalysisSettings>;
  return payload.data;
}

function absolutizeApiPath(path: string): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const base = API_BASE_URL.endsWith("/api/v1") ? API_BASE_URL.slice(0, -"/api/v1".length) : API_BASE_URL;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}
