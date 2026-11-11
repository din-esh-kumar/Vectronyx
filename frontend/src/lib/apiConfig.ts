// frontend/src/lib/apiConfig.ts
declare global {
  interface Window {
    __VECTRONYX_CONFIG__?: {
      apiUrl?: string;
      graphqlUrl?: string;
      supabaseUrl?: string;
      supabasePublishableKey?: string;
    };
  }
}

const runtimeConfig =
  typeof window !== "undefined" ? window.__VECTRONYX_CONFIG__ : undefined;

const env =
  typeof import.meta !== "undefined" && import.meta.env
    ? import.meta.env
    : ({} as Record<string, any>);

/**
 * Resolve backend API base URL:
 * 1. Runtime-injected config (unified container)
 * 2. Explicit VITE_API_URL build env var (Vercel/Netlify -> Render/Railway)
 * 3. In Vite dev server (`DEV`), fallback to http://localhost:8000
 * 4. In production builds without VITE_API_URL, use "" (same-origin relative path)
 */
export const API_URL: string = (() => {
  const configured = runtimeConfig?.apiUrl ?? env.VITE_API_URL;
  if (typeof configured === "string" && configured.trim() !== "") {
    return configured.trim().replace(/\/$/, "");
  }
  return env.DEV ? "http://localhost:8000" : "";
})();

export const GRAPHQL_URL: string = (() => {
  const configured = runtimeConfig?.graphqlUrl ?? env.VITE_GRAPHQL_URL;
  if (typeof configured === "string" && configured.trim() !== "") {
    return configured.trim().replace(/\/$/, "");
  }
  return `${API_URL}/graphql`;
})();

export const SUPABASE_URL: string =
  runtimeConfig?.supabaseUrl ||
  env.VITE_SUPABASE_URL ||
  "https://ynmmhgkarttzpayuxbqh.supabase.co";

export const SUPABASE_PUBLISHABLE_KEY: string =
  runtimeConfig?.supabasePublishableKey ||
  env.VITE_SUPABASE_PUBLISHABLE_KEY ||
  "sb_publishable_h0V9Fdu4tco1OMFBTjYZCA_gUadjdQM";
