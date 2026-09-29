import { Tabs, useRouter } from "expo-router";
import { Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { type } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";

export default function TabLayout() {
  const colors = useColors();
  const router = useRouter();

  return (
    <Tabs
      initialRouteName="index"
      screenOptions={{
        headerStyle: { backgroundColor: colors.parchment },
        headerTintColor: colors.ink,
        headerTitleStyle: {
          fontFamily: type.medium,
          fontSize: 17,
          color: colors.ink,
        },
        headerTitleAlign: "center",
        headerShadowVisible: false,
        headerLeft: () => (
          <Pressable
            onPress={() => router.push("/settings")}
            hitSlop={12}
            style={{ marginStart: 14 }}
            accessibilityLabel="تنظیمات"
          >
            <Ionicons name="settings-outline" size={22} color={colors.ink} />
          </Pressable>
        ),
        headerRight: () => null,
        tabBarActiveTintColor: colors.ink,
        tabBarInactiveTintColor: colors.mist,
        tabBarStyle: {
          backgroundColor: colors.parchment,
          borderTopColor: colors.line,
          height: 78,
          paddingTop: 4,
        },
        tabBarLabelStyle: {
          fontFamily: type.regular,
          fontSize: 11,
          marginBottom: 4,
        },
      }}
    >
      <Tabs.Screen
        name="search"
        options={{
          title: "جستجو",
          tabBarIcon: ({ color, focused }) => (
            <Ionicons
              name={focused ? "search" : "search-outline"}
              size={22}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="saved"
        options={{
          title: "فهرست من",
          tabBarIcon: ({ color }) => (
            <Ionicons name="bookmark-outline" size={22} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="index"
        options={{
          title: "کتابخانه",
          tabBarIcon: ({ color, focused }) => (
            <Ionicons
              name={focused ? "library" : "library-outline"}
              size={22}
              color={color}
            />
          ),
        }}
      />
    </Tabs>
  );
}
