"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const TOKEN_KEY = "rag_access_token";

type LlmModel = {
  id: string;
  label: string;
  cost_label: string;
  note?: string;
};

type UsedChunk = {
  ref: number;
  chunk_id: string;
  text: string;
  char_start: number;
  char_end: number;
  t_start: number | null;
  t_end: number | null;
  lecturer: string;
  course: string;
  session_id: string;
  portal_path?: string;
};

type AskResult = {
  answer: string;
  answer_fa?: string;
  question_fa?: string;
  detected_lang?: string;
  model: { id: string; label: string; cost_label: string };
  used_chunks: UsedChunk[];
  retrieved_count: number;
  used_count: number;
  cost?: {
    currency: string;
    total_usd: number;
    label: string;
    detail: string;
    prompt_tokens: number;
    completion_tokens: number;
    embed_tokens: number;
  };
};

const STAGE_FA: Record<string, string> = {
  detect: "تشخیص زبان…",
  translate_in: "ترجمهٔ سؤال به فارسی…",
  retrieve: "جستجو در درس‌گفتارها…",
  select: "انتخاب قطعات مرتبط…",
  generate: "در حال نوشتن پاسخ…",
};

function apiBase(): string {
  return (
    process.env.NEXT_PUBLIC_RAG_API_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000"
  );
}

function fmtTime(sec: number | null | undefined): string {
  if (sec == null || Number.isNaN(sec)) return "—";
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}

export default function AskPage() {
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [models, setModels] = useState<LlmModel[]>([]);
  const [modelId, setModelId] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  const [streamText, setStreamText] = useState("");
  const [active, setActive] = useState<UsedChunk | null>(null);
  const [fullProse, setFullProse] = useState<string>("");
  const markRef = useRef<HTMLElement | null>(null);
  const scrollBoxRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const t = sessionStorage.getItem(TOKEN_KEY);
    if (t) setToken(t);
  }, []);

  const authHeaders = useMemo(() => {
    if (!token) return {} as Record<string, string>;
    return { Authorization: `Bearer ${token}` };
  }, [token]);

  const loadModels = useCallback(async (t: string) => {
    const res = await fetch(`${apiBase()}/models`, {
      headers: { Authorization: `Bearer ${t}` },
    });
    if (!res.ok) throw new Error("models");
    const data = await res.json();
    setModels(data.models || []);
    setModelId(data.default || data.models?.[0]?.id || "");
  }, []);

  useEffect(() => {
    if (!token) return;
    loadModels(token).catch(() => {
      sessionStorage.removeItem(TOKEN_KEY);
      setToken(null);
    });
  }, [token, loadModels]);

  // Jump modal scroll to highlighted passage once prose is loaded
  useEffect(() => {
    if (!active || !fullProse) return;
    const id = window.requestAnimationFrame(() => {
      markRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    return () => window.cancelAnimationFrame(id);
  }, [active, fullProse]);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginError("");
    try {
      const res = await fetch(`${apiBase()}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        setLoginError("رمز عبور نادرست است.");
        return;
      }
      const data = await res.json();
      sessionStorage.setItem(TOKEN_KEY, data.token);
      setToken(data.token);
      setPassword("");
    } catch {
      setLoginError("سرور RAG در دسترس نیست (آیا روی پورت ۸۰۰۰ روشن است؟).");
    }
  }

  async function onAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || !token) return;
    setLoading(true);
    setError("");
    setResult(null);
    setStreamText("");
    setStage("retrieve");
    setActive(null);

    try {
      const res = await fetch(`${apiBase()}/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...authHeaders,
        },
        body: JSON.stringify({ question, model: modelId, corpus: "manaee", top_k: 10 }),
      });
      if (!res.ok || !res.body) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let liveAnswer = "";
      let meta: Partial<AskResult> = {};

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const block of parts) {
          const line = block
            .split("\n")
            .map((l) => l.trim())
            .find((l) => l.startsWith("data:"));
          if (!line) continue;
          const payload = JSON.parse(line.slice(5).trim());
          if (payload.type === "status") {
            setStage(payload.stage || "");
          } else if (payload.type === "meta") {
            meta = {
              model: payload.model,
              used_chunks: payload.used_chunks || [],
              retrieved_count: payload.retrieved_count || 0,
              used_count: payload.used_count || 0,
              question_fa: payload.question_fa,
              detected_lang: payload.detected_lang,
              answer: "",
            };
            setResult({
              answer: "",
              ...meta,
              model: payload.model,
              used_chunks: payload.used_chunks || [],
              retrieved_count: payload.retrieved_count || 0,
              used_count: payload.used_count || 0,
            } as AskResult);
          } else if (payload.type === "token") {
            liveAnswer += payload.text || "";
            setStreamText(liveAnswer);
            setResult((prev) =>
              prev
                ? { ...prev, answer: liveAnswer }
                : {
                    answer: liveAnswer,
                    model: meta.model || {
                      id: modelId,
                      label: modelId,
                      cost_label: "",
                    },
                    used_chunks: meta.used_chunks || [],
                    retrieved_count: meta.retrieved_count || 0,
                    used_count: meta.used_count || 0,
                  },
            );
          } else if (payload.type === "done") {
            setResult(payload as AskResult);
            setStreamText(payload.answer || liveAnswer);
            setStage("");
          } else if (payload.type === "error") {
            throw new Error(payload.message || "stream error");
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا در پرسش");
    } finally {
      setLoading(false);
      setStage("");
    }
  }

  async function openRef(chunk: UsedChunk) {
    setActive(chunk);
    setFullProse("");
    try {
      const q = new URLSearchParams({
        lecturer: chunk.lecturer,
        course: chunk.course,
        session_id: chunk.session_id,
      });
      const res = await fetch(`${apiBase()}/source?${q}`, {
        headers: authHeaders,
      });
      if (res.ok) {
        const data = await res.json();
        setFullProse(data.prose || "");
      } else {
        setFullProse(chunk.text);
      }
    } catch {
      setFullProse(chunk.text);
    }
  }

  function renderAnswer(text: string, chunks: UsedChunk[]) {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const m = part.match(/^\[(\d+)\]$/);
      if (!m) return <span key={i}>{part}</span>;
      const ref = Number(m[1]);
      const chunk = chunks.find((c) => c.ref === ref);
      if (!chunk) return <span key={i}>{part}</span>;
      return (
        <button
          key={i}
          type="button"
          onClick={() => openRef(chunk)}
          className="mx-0.5 inline-flex h-6 min-w-6 items-center justify-center rounded-md bg-brand-deep px-1.5 text-xs font-bold text-white align-super"
        >
          {ref}
        </button>
      );
    });
  }

  if (!token) {
    return (
      <main className="mx-auto max-w-md space-y-6 py-10">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-black">پرسش از درس‌گفتارها</h1>
          <p className="text-sm leading-7 text-ink/60">
            فقط برای افراد مجاز (حدود ۱۰ نفر). فعلاً فقط درس‌های استاد صبوحی
            (Manaee).
          </p>
        </div>
        <form onSubmit={onLogin} className="card space-y-4 p-6">
          <label className="block space-y-1.5 text-sm">
            <span className="font-medium text-ink/70">رمز دسترسی</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-ink/10 bg-white px-3 py-2.5 outline-none focus:border-brand-deep"
              autoFocus
            />
          </label>
          {loginError ? (
            <p className="text-sm text-red-600">{loginError}</p>
          ) : null}
          <button
            type="submit"
            className="w-full rounded-xl bg-brand-deep py-2.5 text-sm font-bold text-white"
          >
            ورود
          </button>
        </form>
      </main>
    );
  }

  const displayAnswer = result?.answer || streamText;

  return (
    <main className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black">پرسش از درس‌گفتارها</h1>
          <p className="mt-1 text-sm text-ink/55">
            منبع: متن خام جلسات Manaee · پاسخ فقط با ارجاع به قطعات استفاده‌شده
          </p>
        </div>
        <button
          type="button"
          className="text-xs text-ink/45 underline"
          onClick={() => {
            sessionStorage.removeItem(TOKEN_KEY);
            setToken(null);
          }}
        >
          خروج
        </button>
      </div>

      <form onSubmit={onAsk} className="card space-y-4 p-5">
        <label className="block space-y-1.5 text-sm">
          <span className="font-medium text-ink/70">مدل پاسخ‌گو (DeepInfra)</span>
          <select
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            className="w-full rounded-xl border border-ink/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-deep"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label} — {m.cost_label}
                {m.note ? ` · ${m.note}` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-1.5 text-sm">
          <span className="font-medium text-ink/70">سؤال (هر زبانی)</span>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={4}
            placeholder="مثلاً: What does Sura Shams say about purifying the soul?"
            className="w-full rounded-xl border border-ink/10 bg-white px-3 py-2.5 text-sm leading-7 outline-none focus:border-brand-deep"
          />
        </label>
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="rounded-xl bg-brand-deep px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
        >
          {loading ? STAGE_FA[stage] || "در حال تولید پاسخ…" : "بپرس"}
        </button>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </form>

      {result || loading ? (
        <section className="card space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-2 text-xs text-ink/50">
            {result?.model ? (
              <span className="chip">
                {result.model.label} · {result.model.cost_label}
              </span>
            ) : null}
            {result ? (
              <span>
                بازیابی {result.retrieved_count} · استفاده‌شده {result.used_count}
              </span>
            ) : null}
            {loading ? (
              <span className="text-brand-deep">{STAGE_FA[stage] || "…"}</span>
            ) : null}
          </div>
          <div className="min-h-[3rem] text-base leading-8 text-ink">
            {displayAnswer
              ? renderAnswer(displayAnswer, result?.used_chunks || [])
              : loading
                ? "…"
                : null}
            {loading && displayAnswer ? (
              <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-brand-deep align-middle" />
            ) : null}
          </div>
          {result?.cost && !loading ? (
            <p className="border-t border-ink/5 pt-3 text-xs leading-6 text-ink/45">
              هزینه این پاسخ:{" "}
              <span className="font-semibold text-ink/70">{result.cost.label}</span>
              <span className="mx-1.5 text-ink/25">·</span>
              <span>{result.cost.detail}</span>
            </p>
          ) : null}
          {result?.used_chunks?.length ? (
            <ul className="space-y-2 border-t border-ink/10 pt-4">
              {result.used_chunks.map((c) => (
                <li key={c.chunk_id}>
                  <button
                    type="button"
                    onClick={() => openRef(c)}
                    className="w-full rounded-xl border border-ink/10 bg-white/70 px-3 py-2.5 text-right text-sm transition hover:border-brand-deep/40"
                  >
                    <div className="font-bold text-brand-deep">
                      مرجع [{c.ref}] · {c.course}/{c.session_id} ·{" "}
                      {fmtTime(c.t_start)}–{fmtTime(c.t_end)}
                    </div>
                    <div className="mt-1 line-clamp-2 text-ink/60">{c.text}</div>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {active ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-3 sm:items-center">
          <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-bg shadow-xl">
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-ink/10 px-4 py-3">
              <div className="text-sm font-bold">
                مرجع [{active.ref}] · {active.course}/{active.session_id} ·{" "}
                {fmtTime(active.t_start)}
              </div>
              <div className="flex items-center gap-2">
                {active.portal_path ? (
                  <a
                    href={`${active.portal_path}${active.t_start != null ? `?t=${Math.floor(active.t_start)}` : ""}`}
                    className="rounded-lg bg-brand-deep px-3 py-1.5 text-xs font-bold text-white"
                  >
                    پخش از {fmtTime(active.t_start)}
                  </a>
                ) : null}
                <button
                  type="button"
                  className="rounded-lg px-2 py-1 text-sm text-ink/50"
                  onClick={() => setActive(null)}
                >
                  بستن
                </button>
              </div>
            </div>
            <div
              ref={scrollBoxRef}
              className="max-h-[75vh] flex-1 overflow-y-auto px-4 py-4 text-sm leading-8"
            >
              {fullProse ? (
                <>
                  <span>{fullProse.slice(0, active.char_start)}</span>
                  <mark
                    ref={markRef}
                    className="rounded bg-amber-200/80 px-0.5 text-ink scroll-mt-8"
                  >
                    {fullProse.slice(active.char_start, active.char_end)}
                  </mark>
                  <span>{fullProse.slice(active.char_end)}</span>
                </>
              ) : (
                <p className="text-ink/50">در حال بارگذاری متن…</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
