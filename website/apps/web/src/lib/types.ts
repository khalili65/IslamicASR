export type Chapter = {
  index: number;
  title: string;
  start: number;
  end: number;
};

export type SessionSummary = {
  id: string;
  index: number;
  title: string;
  topic: string | null;
  hasTranscript: boolean;
  duration: number | null;
  durationText: string | null;
  recordedAt: number | null;
  chapterCount: number;
};

export type CourseIndex = {
  lecturer: string;
  slug: string;
  title: string;
  description: string;
  cover: string;
  sessionCount: number;
  transcribedCount: number;
  totalSeconds: number;
  totalDurationText: string;
  sessions: SessionSummary[];
};

export type SessionPayload = {
  id: string;
  index: number;
  lecturer: string;
  course: string;
  title: string;
  topic: string | null;
  summary: string | null;
  hasTranscript: boolean;
  audio: {
    url: string;
    filename: string;
    size: number;
    display: string;
    duration: number | null;
    durationText: string | null;
  } | null;
  subtitles: {
    fa: { vtt: string; cues: string; words: string };
  } | null;
  chapters: Chapter[];
  previous: string | null;
  next: string | null;
  recordedAt: number | null;
  sourceName: string | null;
};

export type Cue = {
  i: number;
  start: number;
  end: number;
  text: string;
  kind: "speech" | "quote";
  chapter: number | null;
  block: number;
  translation?: string;
};

export type CuesFile = {
  version: number;
  sessionId: string;
  lang: string;
  duration: number;
  chapters: Chapter[];
  cues: Cue[];
};

export type SiteIndex = {
  version: number;
  mode: "single-lecturer" | "portal";
  defaultLecturer: string;
  brand: {
    name: string;
    tagline?: string;
    logo: string;
    locale: string;
    dir: string;
  };
  theme: Record<string, string>;
  features: Record<string, boolean>;
  lecturers: Array<{
    slug: string;
    name: string;
    title: string;
    bio: string;
    avatar: string;
    courses: Array<{
      slug: string;
      title: string;
      description: string;
      cover: string;
      sessionCount: number;
      transcribedCount: number;
      totalDurationText: string;
    }>;
  }>;
};
