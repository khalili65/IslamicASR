import { useEffect } from "react";
import { I18nManager, View, ActivityIndicator, StyleSheet } from "react-native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import * as SplashScreen from "expo-splash-screen";
import {
  useFonts,
  Vazirmatn_400Regular,
  Vazirmatn_500Medium,
  Vazirmatn_700Bold,
} from "@expo-google-fonts/vazirmatn";
import {
  Amiri_400Regular,
  Amiri_700Bold,
} from "@expo-google-fonts/amiri";
import { type } from "@/constants/theme";
import { useLibraryStore } from "@/lib/store";
import { useThemeStore } from "@/lib/themeStore";
import { useColors, useTheme } from "@/lib/useTheme";

export { ErrorBoundary } from "expo-router";

SplashScreen.preventAutoHideAsync();

// Physical right-align for Farsi; avoid system RTL mirroring.
I18nManager.allowRTL(false);
I18nManager.forceRTL(false);
I18nManager.swapLeftAndRightInRTL(false);

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Vazirmatn_400Regular,
    Vazirmatn_500Medium,
    Vazirmatn_700Bold,
    Amiri_400Regular,
    Amiri_700Bold,
  });
  const load = useLibraryStore((s) => s.load);
  const loadSaved = useLibraryStore((s) => s.loadSaved);
  const hydrateTheme = useThemeStore((s) => s.hydrate);
  const themeHydrated = useThemeStore((s) => s.hydrated);
  const { theme } = useTheme();
  const colors = useColors();

  useEffect(() => {
    void hydrateTheme();
    load();
    loadSaved();
  }, [hydrateTheme, load, loadSaved]);

  useEffect(() => {
    if (fontsLoaded && themeHydrated) SplashScreen.hideAsync();
  }, [fontsLoaded, themeHydrated]);

  if (!fontsLoaded || !themeHydrated) {
    return (
      <View style={[styles.boot, { backgroundColor: colors.parchment }]}>
        <ActivityIndicator color={colors.copper} />
      </View>
    );
  }

  return (
    <>
      <StatusBar style={theme.statusBar} />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.parchment },
          headerTintColor: colors.ink,
          headerTitleStyle: {
            fontFamily: type.bold,
            fontSize: 17,
            color: colors.ink,
          },
          headerTitleAlign: "center",
          headerShadowVisible: false,
          contentStyle: { backgroundColor: colors.parchment },
          headerBackTitle: "بازگشت",
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="lecturer/[slug]" options={{ title: "استاد" }} />
        <Stack.Screen
          name="course/[lecturer]/[course]"
          options={{ title: "درس" }}
        />
        <Stack.Screen
          name="player/[lecturer]/[course]/[session]"
          options={{ title: "پخش", headerShown: false }}
        />
        <Stack.Screen name="settings" options={{ title: "تنظیمات" }} />
      </Stack>
    </>
  );
}

const styles = StyleSheet.create({
  boot: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
});
