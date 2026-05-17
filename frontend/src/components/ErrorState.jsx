import { AlertTriangle, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

export default function ErrorState({
  title = "Unable to load data",
  message = "Something went wrong while loading this view.",
  onRetry,
  retryLabel = "Try Again",
  linkTo,
  linkLabel,
  compact = false,
}) {
  return (
    <div
      className={
        compact
          ? "px-6 py-10"
          : "flex min-h-[50vh] items-center justify-center px-6 py-10"
      }
    >
      <div className="w-full rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-600" />
        <h2 className="mt-4 text-xl font-semibold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm text-slate-600">{message}</p>

        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
            >
              <RefreshCw className="h-4 w-4" />
              {retryLabel}
            </button>
          )}

          {linkTo && linkLabel && (
            <Link
              to={linkTo}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:text-slate-900"
            >
              {linkLabel}
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
