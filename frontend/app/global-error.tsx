"use client";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }): JSX.Element {
  return (
    <html>
      <body>
        <div className="mx-auto mt-10 max-w-xl rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-800">
          <h2 className="text-lg font-semibold">Fatal application error</h2>
          <p className="mt-2 text-sm">{error.message || "Unexpected app failure"}</p>
          <button className="mt-4 rounded-lg bg-rose-600 px-3 py-2 text-sm font-medium text-white" onClick={() => reset()}>
            Reload segment
          </button>
        </div>
      </body>
    </html>
  );
}
