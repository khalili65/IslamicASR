/**
 * تذکار themes — warm paper (default), night, and cool stone.
 * Player stage stays dark in every theme so subtitles stay readable.
 */

export type ThemeId = "warm" | "night" | "cool";

export type ThemeColors = {
  parchment: string;
  parchmentDeep: string;
  card: string;
  ink: string;
  inkSoft: string;
  mist: string;
  sage: string;
  line: string;
  copper: string;
  copperSoft: string;
  copperWash: string;
  stage: string;
  stageFg: string;
  stageMuted: string;
  white: string;
  danger: string;
};

export type ThemeMeta = {
  id: ThemeId;
  label: string;
  hint: string;
  statusBar: "dark" | "light";
  colors: ThemeColors;
};

export const THEMES: Record<ThemeId, ThemeMeta> = {
  warm: {
    id: "warm",
    label: "کاغذی",
    hint: "پس‌زمینهٔ گرم روشن — پیش‌فرض",
    statusBar: "dark",
    colors: {
      parchment: "#F3F0E8",
      parchmentDeep: "#E8E4DA",
      card: "#F3F0E8",
      ink: "#1A2420",
      inkSoft: "#3A4741",
      mist: "#7A8780",
      sage: "#8FA396",
      line: "rgba(26, 36, 32, 0.1)",
      copper: "#8F6240",
      copperSoft: "#C4A574",
      copperWash: "rgba(143, 98, 64, 0.1)",
      stage: "#14100F",
      stageFg: "#F5F0E8",
      stageMuted: "rgba(245, 240, 232, 0.5)",
      white: "#FFFFFF",
      danger: "#8B3A3A",
    },
  },
  night: {
    id: "night",
    label: "شب",
    hint: "پس‌زمینهٔ تیره برای مطالعه در شب",
    statusBar: "light",
    colors: {
      parchment: "#141816",
      parchmentDeep: "#1E2421",
      card: "#1A201D",
      ink: "#E8E4DA",
      inkSoft: "#C5C0B4",
      mist: "#8A928C",
      sage: "#8FA396",
      line: "rgba(232, 228, 218, 0.12)",
      copper: "#C4A574",
      copperSoft: "#A8895E",
      copperWash: "rgba(196, 165, 116, 0.16)",
      stage: "#0C0A09",
      stageFg: "#F5F0E8",
      stageMuted: "rgba(245, 240, 232, 0.45)",
      white: "#FFFFFF",
      danger: "#D48484",
    },
  },
  cool: {
    id: "cool",
    label: "خنک",
    hint: "خاکستری روشن، کمتر گرم",
    statusBar: "dark",
    colors: {
      parchment: "#EEF1F4",
      parchmentDeep: "#E2E7EC",
      card: "#F4F6F8",
      ink: "#1B242C",
      inkSoft: "#3A4652",
      mist: "#7A8794",
      sage: "#7E93A3",
      line: "rgba(27, 36, 44, 0.1)",
      copper: "#5F7388",
      copperSoft: "#8FA3B5",
      copperWash: "rgba(95, 115, 136, 0.12)",
      stage: "#12151A",
      stageFg: "#F0F3F6",
      stageMuted: "rgba(240, 243, 246, 0.5)",
      white: "#FFFFFF",
      danger: "#8B3A3A",
    },
  },
};

export const DEFAULT_THEME_ID: ThemeId = "warm";

/** @deprecated Prefer useColors() — kept for boot splash before store hydrates. */
export const colors: ThemeColors = THEMES.warm.colors;

export const space = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radii = {
  sm: 6,
  md: 10,
  lg: 16,
  pill: 999,
} as const;

export const type = {
  regular: "Vazirmatn_400Regular",
  medium: "Vazirmatn_500Medium",
  bold: "Vazirmatn_700Bold",
} as const;

export const APP_TITLE = "تذکار";

export const SITES = {
  website: {
    id: "website" as const,
    label: "حجت‌الاسلام والمسلمین بیات",
    dataBase: "https://islamic-asr-web.s3-website.ir-thr-at1.arvanstorage.ir",
    mediaBase:
      "https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir",
  },
  portal: {
    id: "portal" as const,
    label: "پورتال",
    dataBase:
      "https://islamic-asr-portal-web.s3-website.ir-thr-at1.arvanstorage.ir",
    mediaBase:
      "https://islamic-asr-portal-media.s3.ir-thr-at1.arvanstorage.ir",
  },
} as const;

export type SiteKey = keyof typeof SITES;

export function isThemeId(value: string): value is ThemeId {
  return value === "warm" || value === "night" || value === "cool";
}
