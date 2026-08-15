/** Turn the hex colours in site.config.json into the `r g b` channel form
 *  that the Tailwind tokens in globals.css expect. */

type Theme = Record<string, string | undefined>;

const VARIABLE_BY_KEY: Record<string, string> = {
  bg: "--bg",
  brand: "--brand",
  brandInk: "--brand-ink",
  brandDeep: "--brand-deep",
  surface: "--surface",
  surface2: "--surface-2",
  subtitleBg: "--subtitle-bg",
  subtitleFg: "--subtitle-fg",
  muted: "--muted",
  track: "--track",
  trackFill: "--track-fill",
  accent: "--accent",
  ink: "--ink",
};

function toChannels(value: string): string | null {
  const hex = value.trim().replace(/^#/, "");
  const full =
    hex.length === 3
      ? hex
          .split("")
          .map((c) => c + c)
          .join("")
      : hex;
  if (!/^[0-9a-f]{6}$/i.test(full)) return null;
  const n = parseInt(full, 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
}

export function themeToCssVars(theme: Theme): string {
  return Object.entries(VARIABLE_BY_KEY)
    .map(([key, variable]) => {
      const value = theme[key];
      if (!value) return null;
      const channels = toChannels(value);
      return channels ? `${variable}:${channels}` : null;
    })
    .filter(Boolean)
    .join(";");
}
