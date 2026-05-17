import { Inbox } from "lucide-react";
import { Link } from "react-router-dom";

export default function EmptyState({
  title = "No data available",
  message = "There is nothing to display right now.",
  linkTo,
  linkLabel,
  compact = false,
}) {
  return (
    <div
      className={
        compact
          ? "px-0 py-0"
          : "flex min-h-[50vh] items-center justify-center px-6 py-10"
      }
    >
      <div className="w-full rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center shadow-sm">
        <Inbox className="mx-auto h-8 w-8 text-slate-400" />
        <h2 className="mt-4 text-xl font-semibold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm text-slate-500">{message}</p>

        {linkTo && linkLabel && (
          <div className="mt-5">
            <Link
              to={linkTo}
              className="inline-flex rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:text-slate-900"
            >
              {linkLabel}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
