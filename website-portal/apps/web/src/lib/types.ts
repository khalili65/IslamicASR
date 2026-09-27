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
  format?: "audio" | "text";
  hasFullText?: boolean;
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
  format?: "audio" | "text";
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
  hasFullText?: boolean;
  hasSummary?: boolean;
  hasBook?: boolean;
  hasRawTranscript?: boolean;
  subtitleSource?: "raw" | "edited" | null;
  hasTranscript: boolean;
  format?: "audio" | "text";
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
    format?: "audio" | "text";
    /** When true, omitted from home/search/static routes (data may remain on disk). */
    hidden?: boolean;
    links?: Array<{ label: string; url: string }>;
    courses: Array<{
      slug: string;
      title: string;
      description: string;
      cover: string;
      sessionCount: number;
      transcribedCount: number;
      totalDurationText: string;
      format?: "audio" | "text";
    }>;
  }>;
};
