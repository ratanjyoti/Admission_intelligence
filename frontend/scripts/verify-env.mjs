const isCiLike = Boolean(process.env.CI || process.env.VERCEL || process.env.VERCEL_ENV);

if (!isCiLike) {
  process.exit(0);
}

const rawApiBase = (process.env.VITE_API_BASE_URL || "").trim();

if (!rawApiBase) {
  console.error(
    "[build] Missing VITE_API_BASE_URL. Configure it in Vercel Project Settings -> Environment Variables."
  );
  process.exit(1);
}

const normalized = rawApiBase.replace(/\/+$/, "").toLowerCase();

if (normalized.includes("localhost") || normalized.includes("127.0.0.1")) {
  console.error(
    `[build] Invalid VITE_API_BASE_URL for deployment: ${rawApiBase}. Use your public backend URL, not localhost.`
  );
  process.exit(1);
}

console.log(`[build] VITE_API_BASE_URL verified: ${rawApiBase}`);
