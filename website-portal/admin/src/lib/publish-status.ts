import fs from "fs";
import path from "path";
import { repoRoot } from "./paths";
import type { SiteId } from "./sites";

export type PublishStepStatus = "pending" | "running" | "done" | "error";

export type PublishStep = {
  name: string;
  status: PublishStepStatus;
  ok?: boolean;
  output?: string;
};

export type PublishStatus = {
  state: "idle" | "running" | "ok" | "error";
  site?: SiteId;
  deploy?: boolean;
  startedAt?: string;
  updatedAt: string;
  finishedAt?: string;
  phase: string;
  detail?: string;
  progress?: { current: number; total: number };
  steps: PublishStep[];
  logTail: string;
  ok?: boolean;
};

const IDLE: PublishStatus = {
  state: "idle",
  updatedAt: new Date().toISOString(),
  phase: "آماده",
  steps: [],
  logTail: "",
};

function statusPath(): string {
  return (
    process.env.PUBLISH_STATUS_FILE ||
    path.join(repoRoot(), ".publish-status.json")
  );
}

export function readPublishStatus(): PublishStatus {
  try {
    const raw = fs.readFileSync(statusPath(), "utf8");
    return { ...IDLE, ...JSON.parse(raw) } as PublishStatus;
  } catch {
    return { ...IDLE };
  }
}

export function writePublishStatus(patch: Partial<PublishStatus>): PublishStatus {
  const prev = readPublishStatus();
  const next: PublishStatus = {
    ...prev,
    ...patch,
    updatedAt: new Date().toISOString(),
    steps: patch.steps ?? prev.steps,
    logTail: patch.logTail ?? prev.logTail,
  };
  const file = statusPath();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(next, null, 2), "utf8");
  return next;
}

export function appendPublishLog(line: string, maxChars = 12000): void {
  const prev = readPublishStatus();
  const merged = `${prev.logTail}${prev.logTail && !prev.logTail.endsWith("\n") ? "\n" : ""}${line}`.slice(
    -maxChars,
  );
  writePublishStatus({ logTail: merged });
}

export function isPublishRunning(): boolean {
  const s = readPublishStatus();
  if (s.state !== "running") return false;
  // Stale lock: if no update for 45 minutes, treat as dead
  const updated = Date.parse(s.updatedAt || "");
  if (!Number.isFinite(updated)) return false;
  return Date.now() - updated < 45 * 60 * 1000;
}
