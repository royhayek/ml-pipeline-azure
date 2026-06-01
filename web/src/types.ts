export interface InferenceRecord {
  id: string;
  blob_name: string;
  timestamp: string;
  model_version: string;
  record_count: number | null;
  latency_ms: number | null;
  confidence_score: number | null;
  hf_summary?: string;
}

export interface ApiMeta {
  read_region: string;
  read_latency_ms: number;
}

export interface ApiResponse {
  data: InferenceRecord[];
  count: number;
  meta?: ApiMeta;
}

export type FetchStatus = "idle" | "loading" | "success" | "error";
