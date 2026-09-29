/**
 * تذکار — quiet library: warm paper, dark ink, one copper accent.
 * Restraint: typography and space carry hierarchy; chrome stays thin.
 */
export const colors = {
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
} as const;

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
    label: "استاد بیات",
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
