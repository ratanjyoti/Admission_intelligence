const isCiLike = Boolean(process.env.CI || process.env.VERCEL || process.env.VERCEL_ENV);

if (!isCiLike) {
  process.exit(0);
}

const rawApiBase = (process.env.VITE_API_BASE_URL || "").trim();

if (!rawApiBase) {
  console.error(
    "[build] VITE_API_BASE_URL is required in deployment. Set it in Vercel for Production, Preview, and Development."
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

if (
  rawApiBase.includes("<")
  || rawApiBase.includes(">")
  || normalized.includes("your-render-backend-service")
  || normalized.includes("example.com")
) {
  console.error(
    `[build] Invalid VITE_API_BASE_URL placeholder detected: ${rawApiBase}. Set a real Render backend URL.`
  );
  process.exit(1);
}

try {
  const parsed = new URL(rawApiBase);
  if (parsed.protocol !== "https:") {
    console.error(`[build] VITE_API_BASE_URL must use https in deployment: ${rawApiBase}`);
    process.exit(1);
  }
} catch {
  console.error(`[build] VITE_API_BASE_URL is not a valid URL: ${rawApiBase}`);
  process.exit(1);
}

console.log(`[build] VITE_API_BASE_URL verified: ${rawApiBase}`);
