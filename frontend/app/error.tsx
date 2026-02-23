"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }): JSX.Element {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto mt-10 max-w-xl rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-800">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="mt-2 text-sm">{error.message || "Unexpected UI error"}</p>
      <button className="mt-4 rounded-lg bg-rose-600 px-3 py-2 text-sm font-medium text-white" onClick={() => reset()}>
        Try again
      </button>
    </div>
  );
}
