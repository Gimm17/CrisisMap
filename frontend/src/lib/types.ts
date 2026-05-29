import type { FeatureCollection, Polygon } from "geojson";

export type AssessmentStatus = "pending" | "running" | "completed" | "failed";
export type DamageTier = "intact" | "minor" | "moderate" | "severe" | "destroyed";
export type ProcessingPriority = "economy" | "standard" | "critical";
export type TokenRouterModel =
  | "anthropic/claude-sonnet-4.6"
  | "openai/gpt-5.4"
  | "moonshotai/kimi-k2.6"
  | "google/gemini-3.1-pro-preview"
  | "x-ai/grok-4.20-beta";

export type ApiEnvelope<T> = {
  success: boolean;
  message: string;
  data: T;
  meta?: Record<string, unknown>;
};

export type AssessmentSummary = {
  buildings_assessed: number;
  severe_or_destroyed: number;
  critical_infrastructure_affected: number;
  estimated_population_impact: number;
  total_damage_score: number;
};

export type TokenRouterMetadata = {
  provider: string;
  model: string;
  routing_mode: string;
  latency_ms: number;
  x_request_id?: string | null;
};

export type Assessment = {
  assessment_id: string;
  name: string;
  mode: "demo" | "live";
  location_name: string;
  status: AssessmentStatus;
  progress: number;
  created_at: string;
  completed_at?: string | null;
  runtime_seconds?: number | null;
  source_status?: Record<string, string>;
  summary?: AssessmentSummary | null;
  tokenrouter?: TokenRouterMetadata | null;
  pipeline?: Record<string, unknown> | null;
};

export type AssessmentCreatePayload = {
  name?: string;
  mode?: "demo" | "live";
  location_name?: string;
  aoi_geojson?: Polygon | null;
  event_date?: string;
  pre_date_start?: string;
  pre_date_end?: string;
  post_date_start?: string;
  post_date_end?: string;
  model_profile?: string;
  processing_priority?: ProcessingPriority;
  tokenrouter_model?: TokenRouterModel;
};

export type AnalysisSettings = {
  model_profile: string;
  tokenrouter_model: TokenRouterModel;
  confidence_threshold: number;
  processing_priority: ProcessingPriority;
  raw_imagery_retention_days: number;
  scrub_metadata_on_export: boolean;
  auto_publish_destroyed_tags: boolean;
  provider_status?: string;
  tokenrouter_base_url?: string;
};

export type DataSourceReadinessItem = {
  status?: string;
  message?: string;
  path?: string | null;
  backend?: string;
  counts?: Record<string, number>;
  [key: string]: unknown;
};

export type DataSourceReadiness = {
  postgis?: DataSourceReadinessItem;
  osm?: DataSourceReadinessItem;
  hdx?: DataSourceReadinessItem;
  ml_model?: DataSourceReadinessItem;
  imagery?: Record<string, DataSourceReadinessItem>;
  xbd?: Record<string, DataSourceReadinessItem>;
  tokenrouter?: DataSourceReadinessItem;
  sentinel?: DataSourceReadinessItem;
  [key: string]: unknown;
};

export type AssessmentArtifacts = {
  assessment_id?: string;
  method?: string | null;
  aoi?: Record<string, unknown> | null;
  chip_artifacts?: Record<string, { pre?: string; post?: string }>;
  validation?: {
    ground_truth_points?: number;
    matched_buildings?: number;
    predicted_severe_or_destroyed?: number;
    metrics?: {
      matched_buildings?: number;
      accuracy?: number;
      macro_f1?: number;
      per_class?: Record<string, { precision?: number; recall?: number; f1?: number; support?: number }>;
      confusion_matrix?: Record<string, Record<string, number>>;
    };
    note?: string;
    [key: string]: unknown;
  } | null;
  exports?: Record<string, string>;
  pipeline_metadata?: Record<string, unknown>;
};

export type ImageryViewMode = "damage" | "after" | "before" | "split";

export type ImageryLayerMetadata = {
  kind: "before" | "after";
  label: string;
  date_label: string;
  status: string;
  tile_url_template: string;
  path?: string;
  crs?: string;
  bounds?: [[number, number], [number, number]];
  width?: number;
  height?: number;
  bands?: number;
  message?: string;
};

export type ImageryMetadata = {
  ready: boolean;
  tile_size: number;
  min_zoom: number;
  max_zoom: number;
  default_bounds?: [[number, number], [number, number]] | null;
  attribution: string;
  layers: {
    before: ImageryLayerMetadata;
    after: ImageryLayerMetadata;
  };
};

export type PriorityBuilding = {
  rank: number;
  building_id: string;
  name: string;
  infrastructure_type: string;
  damage_score: number;
  priority_score: number;
  status: string;
  reasoning: string;
  affected_population: number;
  estimated_cost_usd: number;
  repair_timeline_days: number;
  required_specialists: string[];
  dependencies: string[];
  confidence: number;
};

export type PhasedPlanItem = {
  phase: string;
  label: string;
  actions: string[];
};

export type AssessmentReport = {
  donor_summary: string;
  damage_overview: string;
  priority_buildings: PriorityBuilding[];
  phased_plan: PhasedPlanItem[];
  engineering_notes: string;
  tokenrouter: TokenRouterMetadata;
};

export type BuildingFeatureCollection = FeatureCollection<
  Polygon,
  {
    building_id: string;
    name: string;
    damage_score: number;
    damage_tier: DamageTier;
    infrastructure_type: string;
    population_estimate: number;
    estimated_cost_usd: number;
    confidence: number;
    priority_rank?: number;
    inference_method?: string;
    model_version?: string | null;
    validation_label?: string | null;
    validation_match?: boolean | null;
    evidence?: {
      chip_available?: boolean;
      predicted_class?: string | null;
      baseline_damage_score?: number;
      baseline_change_score?: number;
      [key: string]: unknown;
    } | null;
  }
>;
