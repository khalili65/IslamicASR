import { useThemeStore } from "@/lib/themeStore";
import type { ThemeColors, ThemeId, ThemeMeta } from "@/constants/theme";

export function useColors(): ThemeColors {
  return useThemeStore((s) => s.colors);
}

export function useTheme(): {
  themeId: ThemeId;
  theme: ThemeMeta;
  colors: ThemeColors;
  setThemeId: (id: ThemeId) => Promise<void>;
} {
  const themeId = useThemeStore((s) => s.themeId);
  const theme = useThemeStore((s) => s.theme);
  const colors = useThemeStore((s) => s.colors);
  const setThemeId = useThemeStore((s) => s.setThemeId);
  return { themeId, theme, colors, setThemeId };
}
