import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { colors, type } from "@/constants/theme";

export default function TabLayout() {
  return (
    <Tabs
      initialRouteName="index"
      screenOptions={{
        headerStyle: { backgroundColor: colors.parchment },
        headerTintColor: colors.ink,
        headerTitleStyle: {
          fontFamily: type.medium,
          fontSize: 17,
        },
        headerTitleAlign: "center",
        headerShadowVisible: false,
        headerLeft: () => null,
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
