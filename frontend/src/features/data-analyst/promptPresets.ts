// frontend/src/features/data-analyst/promptPresets.ts

export interface CustomPrompt {
  id: string;
  title: string;
  prompt: string;
  createdAt: string;
}

export const CUSTOM_PROMPTS_STORAGE_KEY = "vectronyx-custom-analysis-prompts";

/**
 * Derive a concise display label when a user saves a custom prompt without an explicit title.
 */
export function derivePromptTitle(promptText: string, explicitTitle?: string): string {
  const trimmedTitle = (explicitTitle || "").trim();
  if (trimmedTitle) return trimmedTitle;

  const firstLine = promptText.trim().split(/\r?\n/)[0].trim();
  if (firstLine.length <= 44) return firstLine;
  return `${firstLine.slice(0, 41).trimEnd()}...`;
}

/**
 * Load saved custom prompts safely from localStorage.
 */
export function loadCustomPrompts(): CustomPrompt[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(CUSTOM_PROMPTS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item): item is CustomPrompt =>
        Boolean(item) &&
        typeof item.id === "string" &&
        typeof item.title === "string" &&
        typeof item.prompt === "string" &&
        item.prompt.trim().length > 0
    );
  } catch {
    return [];
  }
}

/**
 * Persist custom prompts safely to localStorage.
 */
export function saveCustomPrompts(prompts: CustomPrompt[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(CUSTOM_PROMPTS_STORAGE_KEY, JSON.stringify(prompts));
  } catch {
    // Ignore storage quota or private browsing errors
  }
}

/**
 * Create a unique identifier for a newly saved custom prompt.
 */
export function createCustomPromptId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `cp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}
