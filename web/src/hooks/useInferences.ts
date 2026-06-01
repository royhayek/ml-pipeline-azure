import { useState, useEffect, useCallback, useRef } from "react";
import type { InferenceRecord, FetchStatus } from "../types";

const API_URL = "/api/recent";
const POLL_INTERVAL = 30_000;

interface UseInferencesReturn {
  data: InferenceRecord[];
  status: FetchStatus;
  error: string | null;
  lastSync: Date | null;
  isFetching: boolean;
  refresh: () => void;
}

export function useInferences(): UseInferencesReturn {
  const [data, setData] = useState<InferenceRecord[]>([]);
  const [status, setStatus] = useState<FetchStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const fetch_ = useCallback(async () => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setIsFetching(true);
    if (status === "idle") setStatus("loading");

    try {
      const res = await fetch(API_URL, { signal: abortRef.current.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as { data: InferenceRecord[] };
      setData(json.data ?? []);
      setLastSync(new Date());
      setStatus("success");
      setError(null);
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      setStatus("error");
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setIsFetching(false);
    }
  }, [status]);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, POLL_INTERVAL);
    return () => {
      clearInterval(id);
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { data, status, error, lastSync, isFetching, refresh: fetch_ };
}
