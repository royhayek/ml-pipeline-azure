export interface InferenceRecord {
  id: string;
  blob_name: string;
  timestamp: string;
  model_version: string;
  record_count: number | null;
  latency_ms: number | null;
  confidence_score: number | null;
}

export interface ApiResponse {
  data: InferenceRecord[];
  count: number;
}

export type FetchStatus = "idle" | "loading" | "success" | "error";
