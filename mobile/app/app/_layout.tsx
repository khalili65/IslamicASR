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
import { colors, type } from "@/constants/theme";
import { useLibraryStore } from "@/lib/store";

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

  useEffect(() => {
    load();
    loadSaved();
  }, [load, loadSaved]);

  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync();
  }, [fontsLoaded]);

  if (!fontsLoaded) {
    return (
      <View style={styles.boot}>
        <ActivityIndicator color={colors.copper} />
      </View>
    );
  }

  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.parchment },
          headerTintColor: colors.ink,
          headerTitleStyle: {
            fontFamily: type.bold,
            fontSize: 17,
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
      </Stack>
    </>
  );
}

const styles = StyleSheet.create({
  boot: {
    flex: 1,
    backgroundColor: colors.parchment,
    alignItems: "center",
    justifyContent: "center",
  },
});
