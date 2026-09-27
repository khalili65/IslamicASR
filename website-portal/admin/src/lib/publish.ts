import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { paths, pathsFor, repoRoot, siteArvanDefaults, siteRoot } from "./paths";
import type { SiteId } from "./sites";
import {
  appendPublishLog,
  isPublishRunning,
  readPublishStatus,
  writePublishStatus,
  type PublishStep,
} from "./publish-status";

export type PublishResult = {
  ok: boolean;
  steps: { name: string; ok: boolean; output: string }[];
};

function loadRepoEnvFile(name: string): Record<string, string> {
  const file = path.join(repoRoot(), name);
  if (!fs.existsSync(file)) return {};
  const out: Record<string, string> = {};
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    out[key] = val;
  }
  return out;
}

function arvanEnv(siteId: SiteId): Record<string, string> {
  const defaults = siteArvanDefaults(siteId);
  const fromFile = loadRepoEnvFile(".env.arvan");
  return {
    ARVAN_ACCESS_KEY:
      process.env.ARVAN_ACCESS_KEY || fromFile.ARVAN_ACCESS_KEY || "",
    ARVAN_SECRET_KEY:
      process.env.ARVAN_SECRET_KEY || fromFile.ARVAN_SECRET_KEY || "",
    ARVAN_WEB_BUCKET: defaults.webBucket,
    ARVAN_ENDPOINT:
      process.env.ARVAN_ENDPOINT ||
      fromFile.ARVAN_ENDPOINT ||
      "https://s3.ir-thr-at1.arvanstorage.ir",
    ARVAN_REGION:
      process.env.ARVAN_REGION || fromFile.ARVAN_REGION || "ir-thr-at1",
    NEXT_PUBLIC_MEDIA_BASE: defaults.mediaBase,
  };
}

function parseProgress(line: string): { current: number; total: number } | null {
  const m = line.match(/\[(\d+)\s*\/\s*(\d+)\]/);
  if (!m) return null;
  return { current: Number(m[1]), total: Number(m[2]) };
}

function runStreaming(
  cmd: string,
  args: string[],
  cwd: string,
  extraEnv: Record<string, string> | undefined,
  onChunk?: (text: string) => void,
): Promise<{ ok: boolean; output: string }> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, {
      cwd,
      env: { ...process.env, ...extraEnv },
    });
    let output = "";
    let lineBuf = "";

    const handle = (chunk: Buffer) => {
      const text = chunk.toString("utf8");
      output += text;
      lineBuf += text;
      const parts = lineBuf.split(/\r?\n/);
      lineBuf = parts.pop() || "";
      for (const line of parts) {
        if (!line.trim()) continue;
        onChunk?.(line);
      }
    };

    child.stdout?.on("data", handle);
    child.stderr?.on("data", handle);
    child.on("error", (err) => {
      resolve({ ok: false, output: `${output}\n${err.message}`.trim() });
    });
    child.on("close", (code) => {
      if (lineBuf.trim()) onChunk?.(lineBuf.trim());
      resolve({ ok: code === 0, output: output.trim() });
    });
  });
}

function setSteps(steps: PublishStep[]) {
  writePublishStatus({ steps });
}

function markStep(
  steps: PublishStep[],
  index: number,
  patch: Partial<PublishStep>,
) {
  const next = steps.map((s, i) => (i === index ? { ...s, ...patch } : s));
  setSteps(next);
  return next;
}

async function publishSiteAsync(options: {
  site: SiteId;
  deploy?: boolean;
}): Promise<PublishResult> {
  const siteId = options.site;
  const resultSteps: PublishResult["steps"] = [];
  const repo = repoRoot();
  const py = paths.python();
  const buildScript = paths.buildScript();
  const sitePaths = pathsFor(siteId);
  const arvan = arvanEnv(siteId);

  const planned: PublishStep[] = [
    { name: `آماده‌سازی محتوا (${siteId})`, status: "pending" },
    { name: `نصب وابستگی‌ها (${siteId})`, status: "pending" },
    { name: `ساخت سایت (${siteId})`, status: "pending" },
  ];
  if (options.deploy) {
    planned.push({
      name: `آپلود Arvan (${arvan.ARVAN_WEB_BUCKET})`,
      status: "pending",
    });
  }

  let steps = planned;
  writePublishStatus({
    state: "running",
    site: siteId,
    deploy: Boolean(options.deploy),
    startedAt: new Date().toISOString(),
    finishedAt: undefined,
    phase: "شروع انتشار",
    detail: options.deploy
      ? "ساخت کامل سایت + آپلود به Arvan"
      : "ساخت کامل سایت (بدون آپلود)",
    progress: undefined,
    steps,
    logTail: "",
    ok: undefined,
  });
  appendPublishLog(
    `شروع انتشار «${siteId}»${options.deploy ? " با آپلود Arvan" : ""}.\n` +
      "توجه: حتی با تغییر یک درس، کل سایت دوباره ساخته می‌شود.",
  );

  const finish = (ok: boolean) => {
    writePublishStatus({
      state: ok ? "ok" : "error",
      ok,
      finishedAt: new Date().toISOString(),
      phase: ok ? "تمام شد" : "خطا",
      progress: undefined,
    });
    return { ok, steps: resultSteps };
  };

  if (!fs.existsSync(py)) {
    steps = markStep(steps, 0, {
      status: "error",
      ok: false,
      output: `Python not found at ${py}`,
    });
    resultSteps.push({
      name: steps[0].name,
      ok: false,
      output: steps[0].output || "",
    });
    appendPublishLog(`خطا: Python پیدا نشد (${py})`);
    return finish(false);
  }

  // --- content build ---
  steps = markStep(steps, 0, { status: "running" });
  writePublishStatus({
    phase: "آماده‌سازی محتوا",
    detail: "build_content.py",
  });
  const contentStep = await runStreaming(
    py,
    [buildScript, "--site-root", siteRoot(siteId), "--skip-subtitles"],
    repo,
    undefined,
    (line) => {
      appendPublishLog(line);
      writePublishStatus({ detail: line.slice(0, 160) });
    },
  );
  steps = markStep(steps, 0, {
    status: contentStep.ok ? "done" : "error",
    ok: contentStep.ok,
    output: contentStep.output.slice(-2000),
  });
  resultSteps.push({
    name: `build_content.py (${siteId})`,
    ...contentStep,
  });
  if (!contentStep.ok) {
    appendPublishLog("خطا در آماده‌سازی محتوا");
    return finish(false);
  }

  const webDir = sitePaths.siteWeb();
  if (!fs.existsSync(path.join(webDir, "package.json"))) {
    steps = markStep(steps, 2, {
      status: "error",
      ok: false,
      output: `Missing ${webDir}/package.json`,
    });
    resultSteps.push({
      name: `next build (${siteId})`,
      ok: false,
      output: `Missing ${webDir}/package.json — sync site apps/web to the VPS.`,
    });
    appendPublishLog("package.json سایت پیدا نشد");
    return finish(false);
  }

  // --- npm install (skip when node_modules already present) ---
  steps = markStep(steps, 1, { status: "running" });
  const hasModules = fs.existsSync(path.join(webDir, "node_modules", "next"));
  if (hasModules) {
    const msg = "node_modules موجود است — نصب رد شد";
    appendPublishLog(msg);
    steps = markStep(steps, 1, {
      status: "done",
      ok: true,
      output: msg,
    });
    resultSteps.push({
      name: `npm install (${siteId})`,
      ok: true,
      output: msg,
    });
    writePublishStatus({
      phase: "نصب وابستگی‌ها",
      detail: msg,
    });
  } else {
    writePublishStatus({
      phase: "نصب وابستگی‌ها",
      detail: "npm install --include=dev",
    });
    const npmInstall = await runStreaming(
      "npm",
      ["install", "--include=dev"],
      webDir,
      { NODE_ENV: "development" },
      (line) => appendPublishLog(line),
    );
    steps = markStep(steps, 1, {
      status: npmInstall.ok ? "done" : "error",
      ok: npmInstall.ok,
      output: npmInstall.output.slice(-2000),
    });
    resultSteps.push({ name: `npm install (${siteId})`, ...npmInstall });
    if (!npmInstall.ok) {
      appendPublishLog("خطا در npm install");
      return finish(false);
    }
  }

  // --- next build ---
  steps = markStep(steps, 2, { status: "running" });
  writePublishStatus({
    phase: "ساخت سایت (Next.js)",
    detail: "ممکن است ۲ تا ۵ دقیقه طول بکشد…",
    progress: undefined,
  });
  appendPublishLog("شروع next build…");
  const npmBuild = await runStreaming(
    "npm",
    ["run", "build"],
    webDir,
    {
      NEXT_PUBLIC_MEDIA_BASE: arvan.NEXT_PUBLIC_MEDIA_BASE,
      NODE_ENV: "production",
      NODE_OPTIONS: "--max-old-space-size=2048",
    },
    (line) => {
      appendPublishLog(line);
      const prog = parseProgress(line);
      writePublishStatus({
        detail: line.slice(0, 180),
        ...(prog ? { progress: prog } : {}),
      });
    },
  );
  steps = markStep(steps, 2, {
    status: npmBuild.ok ? "done" : "error",
    ok: npmBuild.ok,
    output: npmBuild.output.slice(-3000),
  });
  resultSteps.push({ name: `next build (${siteId})`, ...npmBuild });
  if (!npmBuild.ok) {
    appendPublishLog("خطا در next build");
    return finish(false);
  }

  if (options.deploy) {
    const deployIdx = 3;
    steps = markStep(steps, deployIdx, { status: "running" });
    writePublishStatus({
      phase: "آپلود به Arvan",
      detail: "بررسی و آپلود فایل‌های استاتیک…",
      progress: undefined,
    });
    appendPublishLog(`آپلود به bucket ${arvan.ARVAN_WEB_BUCKET}…`);
    const deployScript = sitePaths.deployScript();
    const outDir = `${webDir}/out`;
    const deploy = await runStreaming(
      py,
      [deployScript],
      repo,
      {
        OUT_DIR: outDir,
        ARVAN_WEB_BUCKET: arvan.ARVAN_WEB_BUCKET,
        ARVAN_ACCESS_KEY: arvan.ARVAN_ACCESS_KEY,
        ARVAN_SECRET_KEY: arvan.ARVAN_SECRET_KEY,
        ARVAN_ENDPOINT: arvan.ARVAN_ENDPOINT,
        ARVAN_REGION: arvan.ARVAN_REGION,
      },
      (line) => {
        appendPublishLog(line);
        const prog = parseProgress(line);
        writePublishStatus({
          detail: line.slice(0, 200),
          ...(prog ? { progress: prog } : {}),
        });
      },
    );
    steps = markStep(steps, deployIdx, {
      status: deploy.ok ? "done" : "error",
      ok: deploy.ok,
      output: deploy.output.slice(-3000),
    });
    resultSteps.push({
      name: `deploy Arvan (${arvan.ARVAN_WEB_BUCKET})`,
      ...deploy,
    });
    if (!deploy.ok) {
      appendPublishLog("خطا در آپلود Arvan");
      return finish(false);
    }
  }

  appendPublishLog("انتشار با موفقیت تمام شد.");
  return finish(true);
}

/** Fire-and-forget publish; returns false if already running. */
export function startPublish(options: {
  site: SiteId;
  deploy?: boolean;
}): { started: boolean; status: ReturnType<typeof readPublishStatus> } {
  if (isPublishRunning()) {
    return { started: false, status: readPublishStatus() };
  }

  writePublishStatus({
    state: "running",
    site: options.site,
    deploy: Boolean(options.deploy),
    startedAt: new Date().toISOString(),
    finishedAt: undefined,
    phase: "در صف…",
    detail: "در حال شروع",
    progress: undefined,
    steps: [],
    logTail: "",
    ok: undefined,
  });

  void publishSiteAsync(options).catch((err) => {
    appendPublishLog(`خطای غیرمنتظره: ${err?.message || err}`);
    writePublishStatus({
      state: "error",
      ok: false,
      finishedAt: new Date().toISOString(),
      phase: "خطا",
      detail: String(err?.message || err),
    });
  });

  return { started: true, status: readPublishStatus() };
}

/** @deprecated sync API kept for scripts — prefer startPublish */
export function publishSite(options: {
  site: SiteId;
  deploy?: boolean;
}): PublishResult {
  // Blocking path unused by HTTP now; still available if needed.
  // Use child_process sync via deasync-less approach: not ideal.
  // Callers should use startPublish.
  throw new Error("Use startPublish() + poll status instead of publishSite()");
}
