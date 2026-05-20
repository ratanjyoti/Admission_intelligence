const isCiLike = Boolean(process.env.CI || process.env.VERCEL || process.env.VERCEL_ENV);
const fallbackApiBase = "https://admission-intelligence-1.onrender.com";

if (!isCiLike) {
  process.exit(0);
}

const rawApiBase = (process.env.VITE_API_BASE_URL || "").trim();
const effectiveApiBase = rawApiBase || fallbackApiBase;

if (!rawApiBase) {
  console.warn(
    `[build] VITE_API_BASE_URL is missing; using fallback ${fallbackApiBase}. Set VITE_API_BASE_URL in Vercel to override.`
  );
}

const normalized = effectiveApiBase.replace(/\/+$/, "").toLowerCase();

if (normalized.includes("localhost") || normalized.includes("127.0.0.1")) {
  console.error(
    `[build] Invalid VITE_API_BASE_URL for deployment: ${effectiveApiBase}. Use your public backend URL, not localhost.`
  );
  process.exit(1);
}

if (
  effectiveApiBase.includes("<")
  || effectiveApiBase.includes(">")
  || normalized.includes("your-render-backend-service")
  || normalized.includes("example.com")
) {
  console.error(
    `[build] Invalid VITE_API_BASE_URL placeholder detected: ${effectiveApiBase}. Set a real Render backend URL.`
  );
  process.exit(1);
}

try {
  const parsed = new URL(effectiveApiBase);
  if (parsed.protocol !== "https:") {
    console.error(`[build] VITE_API_BASE_URL must use https in deployment: ${effectiveApiBase}`);
    process.exit(1);
  }
} catch {
  console.error(`[build] VITE_API_BASE_URL is not a valid URL: ${effectiveApiBase}`);
  process.exit(1);
}

console.log(`[build] VITE_API_BASE_URL verified: ${effectiveApiBase}`);
