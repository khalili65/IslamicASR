import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import {
  DEFAULT_THEME_ID,
  THEMES,
  isThemeId,
  type ThemeColors,
  type ThemeId,
  type ThemeMeta,
} from "@/constants/theme";

const THEME_KEY = "tazkar-theme-id";

type ThemeState = {
  themeId: ThemeId;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setThemeId: (id: ThemeId) => Promise<void>;
  theme: ThemeMeta;
  colors: ThemeColors;
};

export const useThemeStore = create<ThemeState>((set, get) => ({
  themeId: DEFAULT_THEME_ID,
  hydrated: false,
  theme: THEMES[DEFAULT_THEME_ID],
  colors: THEMES[DEFAULT_THEME_ID].colors,
  async hydrate() {
    try {
      const raw = await AsyncStorage.getItem(THEME_KEY);
      if (raw && isThemeId(raw)) {
        set({
          themeId: raw,
          theme: THEMES[raw],
          colors: THEMES[raw].colors,
          hydrated: true,
        });
        return;
      }
    } catch {
      /* ignore */
    }
    set({ hydrated: true });
  },
  async setThemeId(id) {
    if (get().themeId === id) return;
    set({
      themeId: id,
      theme: THEMES[id],
      colors: THEMES[id].colors,
    });
    try {
      await AsyncStorage.setItem(THEME_KEY, id);
    } catch {
      /* ignore */
    }
  },
}));
