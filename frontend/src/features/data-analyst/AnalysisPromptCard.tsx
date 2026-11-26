// frontend/src/features/data-analyst/AnalysisPromptCard.tsx
import React, { useEffect, useRef, useState } from "react";
import {
  Bookmark,
  Check,
  Pencil,
  Plus,
  RefreshCw,
  RotateCcw,
  Sparkles,
  Target,
  Trash2,
  X,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  type CustomPrompt,
  createCustomPromptId,
  derivePromptTitle,
  loadCustomPrompts,
  saveCustomPrompts,
} from "./promptPresets";

interface AnalysisPromptCardProps {
  userPrompt: string;
  setUserPrompt: (value: string) => void;
  dynamicPromptChips: string[];
  loading: boolean;
  refinementIterations: number;
  setRefinementIterations: (n: number) => void;
  streamingStatus: string;
  iterationLog: string[];
  onGenerate: () => void;
  textareaRef?: React.RefObject<HTMLTextAreaElement>;
}

const REFINEMENT_OPTIONS = [
  { n: 1, label: "1× Draft" },
  { n: 3, label: "3× Senior" },
  { n: 5, label: "5× Principal" },
  { n: 8, label: "8× Boardroom" },
];

export const AnalysisPromptCard: React.FC<AnalysisPromptCardProps> = ({
  userPrompt,
  setUserPrompt,
  dynamicPromptChips,
  loading,
  refinementIterations,
  setRefinementIterations,
  streamingStatus,
  iterationLog,
  onGenerate,
  textareaRef,
}) => {
  const internalTextareaRef = useRef<HTMLTextAreaElement>(null);
  const promptInputRef = textareaRef ?? internalTextareaRef;

  const [customPrompts, setCustomPrompts] = useState<CustomPrompt[]>(() =>
    loadCustomPrompts()
  );
  const [composerOpen, setComposerOpen] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState<string>("");
  const [draftPrompt, setDraftPrompt] = useState<string>("");

  useEffect(() => {
    saveCustomPrompts(customPrompts);
  }, [customPrompts]);

  const trimmedActivePrompt = userPrompt.trim();
  const isAlreadySavedCustom = customPrompts.some(
    (item) => item.prompt.trim() === trimmedActivePrompt
  );
  const isPredefinedActive = dynamicPromptChips.some(
    (chip) => chip.trim() === trimmedActivePrompt
  );

  const openNewComposer = (prefillPrompt = "") => {
    setEditingId(null);
    setDraftTitle("");
    setDraftPrompt(prefillPrompt);
    setComposerOpen(true);
  };

  const openEditComposer = (item: CustomPrompt) => {
    setEditingId(item.id);
    setDraftTitle(item.title);
    setDraftPrompt(item.prompt);
    setComposerOpen(true);
  };

  const closeComposer = () => {
    setComposerOpen(false);
    setEditingId(null);
    setDraftTitle("");
    setDraftPrompt("");
  };

  const handleSaveCustomPrompt = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanedPrompt = draftPrompt.trim();
    if (!cleanedPrompt) {
      toast.error("Please enter prompt instructions before saving");
      return;
    }

    const title = derivePromptTitle(cleanedPrompt, draftTitle);

    if (editingId) {
      setCustomPrompts((prev) =>
        prev.map((item) =>
          item.id === editingId
            ? { ...item, title, prompt: cleanedPrompt }
            : item
        )
      );
      setUserPrompt(cleanedPrompt);
      toast.success("Updated custom prompt");
      closeComposer();
      return;
    }

    const duplicate = customPrompts.find(
      (item) => item.prompt.trim() === cleanedPrompt
    );
    if (duplicate) {
      setUserPrompt(duplicate.prompt);
      toast.success(`Selected existing prompt "${duplicate.title}"`);
      closeComposer();
      return;
    }

    const created: CustomPrompt = {
      id: createCustomPromptId(),
      title,
      prompt: cleanedPrompt,
      createdAt: new Date().toISOString(),
    };
    setCustomPrompts((prev) => [created, ...prev]);
    setUserPrompt(cleanedPrompt);
    toast.success(`Saved custom prompt "${title}"`);
    closeComposer();
  };

  const handleDeleteCustomPrompt = (item: CustomPrompt) => {
    setCustomPrompts((prev) => prev.filter((p) => p.id !== item.id));
    if (editingId === item.id) {
      closeComposer();
    }
    toast.success(`Deleted "${item.title}"`);
  };

  const handleClearPrompt = () => {
    setUserPrompt("");
    promptInputRef.current?.focus();
  };

  return (
    <div className="lg:col-span-7 p-5 rounded-2xl glass-card-bronze border border-amber-500/25 flex flex-col justify-between space-y-4">
      <div className="space-y-3">
        {/* Card Header & Quick Prompt Actions */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-amber-200 flex items-center gap-2">
              <Target className="w-4 h-4 text-amber-400" />
              <span>2. Analysis Prompt</span>
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-violet-500/30 bg-violet-950/50 text-violet-200">
              {isAlreadySavedCustom
                ? "Saved Custom"
                : isPredefinedActive
                ? "Predefined"
                : "Custom"}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {trimmedActivePrompt.length > 0 && (
              <button
                type="button"
                onClick={handleClearPrompt}
                disabled={loading}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium text-violet-200/85 hover:text-white bg-violet-950/50 hover:bg-violet-900/60 border border-violet-500/25 transition cursor-pointer disabled:opacity-50"
                title="Clear prompt to type your own"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Clear</span>
              </button>
            )}

            {trimmedActivePrompt.length > 0 && !isAlreadySavedCustom && (
              <button
                type="button"
                onClick={() => openNewComposer(userPrompt)}
                disabled={loading}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium text-amber-200 hover:text-white bg-amber-950/45 hover:bg-amber-900/50 border border-amber-500/30 transition cursor-pointer disabled:opacity-50"
                title="Save current prompt text as a reusable custom prompt"
              >
                <Bookmark className="w-3 h-3 text-amber-400" />
                <span>Save Prompt</span>
              </button>
            )}

            <button
              type="button"
              onClick={() =>
                composerOpen && !editingId ? closeComposer() : openNewComposer("")
              }
              disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold text-white bg-violet-700/75 hover:bg-violet-600/85 border border-violet-400/40 transition cursor-pointer disabled:opacity-50"
            >
              {composerOpen && !editingId ? (
                <>
                  <X className="w-3 h-3" />
                  <span>Close</span>
                </>
              ) : (
                <>
                  <Plus className="w-3 h-3" />
                  <span>Add Custom Prompt</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Direct Custom Prompt Editor */}
        <div className="space-y-1">
          <textarea
            ref={promptInputRef}
            value={userPrompt}
            onChange={(e) => setUserPrompt(e.target.value)}
            rows={3}
            placeholder="Write your own custom analytical prompt, variance question, or decision hypothesis..."
            aria-label="Analysis Prompt"
            className="w-full text-xs sm:text-sm border border-violet-500/35 hover:border-violet-400/50 bg-violet-950/50 rounded-xl p-3 focus-vb text-white resize-y min-h-[84px] font-sans placeholder-violet-300/45 transition"
          />
          <div className="flex items-center justify-between text-[11px] text-violet-300/70">
            <span>
              Type any custom prompt directly above, or select/create a saved preset below.
            </span>
            <span className="font-mono shrink-0 ml-2">
              {userPrompt.length} chars
            </span>
          </div>
        </div>

        {/* Inline Custom Prompt Creation / Edit Form */}
        {composerOpen && (
          <form
            onSubmit={handleSaveCustomPrompt}
            className="p-3.5 rounded-xl bg-violet-950/60 border border-amber-400/35 space-y-2.5 animate-fadeIn"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-amber-200 flex items-center gap-1.5">
                <Bookmark className="w-3.5 h-3.5 text-amber-400" />
                <span>{editingId ? "Edit Custom Prompt" : "New Custom Prompt"}</span>
              </span>
              <button
                type="button"
                onClick={closeComposer}
                className="text-violet-300/70 hover:text-white p-0.5 cursor-pointer"
                aria-label="Cancel custom prompt"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <input
              type="text"
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              placeholder="Prompt title (optional, e.g. Cohort Churn Deep Dive)"
              maxLength={80}
              className="w-full text-xs border border-violet-500/30 bg-black/30 rounded-lg px-3 py-2 focus-vb text-white placeholder-violet-300/45"
            />

            <textarea
              value={draftPrompt}
              onChange={(e) => setDraftPrompt(e.target.value)}
              rows={3}
              placeholder="Enter custom analysis instructions (e.g. Identify top 5 revenue churn drivers by region and build a 90-day retention action plan)..."
              className="w-full text-xs border border-violet-500/30 bg-black/30 rounded-lg p-2.5 focus-vb text-white resize-y placeholder-violet-300/45"
              required
            />

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={closeComposer}
                className="px-3 py-1.5 rounded-lg text-xs text-violet-200/80 hover:text-white bg-violet-950/60 border border-violet-500/25 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white bg-gradient-to-r from-violet-700 to-[#884F2E] hover:from-violet-600 hover:to-[#A36B4A] border border-amber-400/35 transition cursor-pointer"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{editingId ? "Update & Use" : "Save & Use Prompt"}</span>
              </button>
            </div>
          </form>
        )}

        {/* Saved Custom Prompts */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-amber-300/85 font-semibold">
              My Custom Prompts ({customPrompts.length})
            </span>
          </div>

          {customPrompts.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {customPrompts.map((item) => {
                const isSelected = trimmedActivePrompt === item.prompt.trim();
                return (
                  <div
                    key={item.id}
                    className={`inline-flex items-center rounded-lg border transition ${
                      isSelected
                        ? "bg-amber-500/20 border-amber-400/60 text-amber-100"
                        : "bg-amber-950/35 hover:bg-amber-950/55 border-amber-500/25 text-amber-200"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setUserPrompt(item.prompt)}
                      title={item.prompt}
                      className="text-xs px-2.5 py-1 text-left cursor-pointer flex items-center gap-1.5 max-w-[260px]"
                    >
                      <Bookmark className="w-3 h-3 text-amber-400 shrink-0" />
                      <span className="truncate">{item.title}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => openEditComposer(item)}
                      title="Edit custom prompt"
                      aria-label={`Edit ${item.title}`}
                      className="p-1 text-amber-300/70 hover:text-white transition cursor-pointer"
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteCustomPrompt(item)}
                      title="Delete custom prompt"
                      aria-label={`Delete ${item.title}`}
                      className="pr-2 pl-0.5 py-1 text-amber-300/70 hover:text-rose-300 transition cursor-pointer"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-[11px] text-violet-300/60">
              No custom prompts saved yet. Type in the box above or click{" "}
              <button
                type="button"
                onClick={() => openNewComposer("")}
                className="text-amber-300 hover:text-amber-200 underline underline-offset-2 cursor-pointer"
              >
                + Add Custom Prompt
              </button>{" "}
              to save your own reusable prompts.
            </p>
          )}
        </div>

        {/* Predefined Dataset-Aware Prompts */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-mono uppercase tracking-wider text-violet-300/75 font-semibold block">
            Predefined Prompts
          </span>
          <div className="flex flex-wrap gap-1.5">
            {dynamicPromptChips.map((chip) => {
              const isSelected = trimmedActivePrompt === chip.trim();
              return (
                <button
                  key={chip}
                  type="button"
                  onClick={() => setUserPrompt(chip)}
                  className={`text-xs px-2.5 py-1 rounded-lg border transition cursor-pointer text-left ${
                    isSelected
                      ? "bg-violet-700/45 border-violet-400/60 text-white"
                      : "bg-violet-900/30 hover:bg-violet-800/40 text-violet-200 border-violet-500/20"
                  }`}
                >
                  + {chip}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Refinement Passes & Generate Trigger */}
      <div className="space-y-3 pt-3 border-t border-amber-500/15">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono">
            <span className="text-amber-300/90 font-semibold">
              Refinement Passes (16K Max Tokens):
            </span>
            {REFINEMENT_OPTIONS.map((opt) => (
              <button
                key={opt.n}
                type="button"
                disabled={loading}
                onClick={() => setRefinementIterations(opt.n)}
                className={`px-2.5 py-1 rounded-lg border transition cursor-pointer ${
                  refinementIterations === opt.n
                    ? "bg-amber-500/25 text-amber-200 border-amber-400/60 font-bold"
                    : "bg-violet-950/50 text-violet-300/75 border-violet-500/20 hover:border-amber-400/35"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <span className="text-[10px] font-mono text-emerald-300/80">
            Target ≥ 92/100 · 3-Page Power BI (.pbip)
          </span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            {loading && streamingStatus && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-mono text-amber-300 animate-fadeIn">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0 text-amber-400" />
                  <span className="truncate">{streamingStatus}</span>
                </div>
                {iterationLog.length > 1 && (
                  <div className="max-h-20 overflow-y-auto space-y-0.5 pl-5 text-[10px] font-mono text-violet-300/70">
                    {iterationLog.slice(0, -1).map((line, i) => (
                      <div key={i} className="truncate">
                        ✓ {line}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onGenerate}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-violet-700 via-purple-800 to-[#884F2E] hover:from-violet-600 hover:to-[#A36B4A] disabled:opacity-50 text-white font-bold text-xs sm:text-sm transition shadow-lg shadow-violet-950/40 cursor-pointer active:scale-95 border border-[#E8A276]/30 shrink-0"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-[#E8A276]" />
                <span>Refining ({refinementIterations}×)...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-[#E8A276]" />
                <span>Generate Principal Report ({refinementIterations}×)</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
