import { LoaderCircle } from "lucide-react";

export default function LoadingScreen({
  title = "Loading...",
  message = "Preparing the latest hospital intelligence view.",
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
      <div className="w-full rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <LoaderCircle className="mx-auto h-8 w-8 animate-spin text-slate-500" />
        <h2 className="mt-4 text-xl font-semibold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm text-slate-500">{message}</p>
      </div>
    </div>
  );
}
