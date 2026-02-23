"use client";

import useSWR, { type SWRConfiguration } from "swr";

const defaultConfig: SWRConfiguration = {
  refreshInterval: 10000,
  revalidateOnFocus: true,
  revalidateOnReconnect: true,
  dedupingInterval: 1000,
  keepPreviousData: true
};

export function useLiveQuery<T>(key: string | null, fetcher: (() => Promise<T>) | null, config?: SWRConfiguration) {
  const swr = useSWR<T>(key, fetcher, {
    ...defaultConfig,
    ...(config || {})
  });

  return {
    data: swr.data,
    loading: swr.isLoading,
    error: swr.error ? (swr.error instanceof Error ? swr.error.message : String(swr.error)) : null,
    refresh: swr.mutate,
    isValidating: swr.isValidating
  };
}
