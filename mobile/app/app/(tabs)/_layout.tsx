import { Pressable, View, StyleSheet } from "react-native";
import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { colors, radii, type } from "@/constants/theme";

function TabIcon({
  name,
  color,
  focused,
}: {
  name: keyof typeof Ionicons.glyphMap;
  color: string;
  focused: boolean;
}) {
  return (
    <View style={[styles.iconWrap, focused && styles.iconWrapActive]}>
      <Ionicons name={name} size={22} color={color} />
    </View>
  );
}

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
        tabBarActiveTintColor: colors.copper,
        tabBarInactiveTintColor: colors.mist,
        tabBarStyle: {
          backgroundColor: colors.parchment,
          borderTopColor: colors.line,
          height: 84,
          paddingTop: 6,
        },
        tabBarLabelStyle: {
          fontFamily: type.medium,
          fontSize: 11,
          marginBottom: 6,
        },
        headerLeft: () => (
          <Pressable
            accessibilityLabel="تنظیمات"
            hitSlop={12}
            style={styles.settingsBtn}
            onPress={() => {
              /* settings later */
            }}
          >
            <Ionicons name="settings-outline" size={22} color={colors.inkSoft} />
          </Pressable>
        ),
      }}
    >
      <Tabs.Screen
        name="saved"
        options={{
          title: "فهرست من",
          tabBarIcon: ({ color, focused }) => (
            <TabIcon
              name={focused ? "bookmark" : "bookmark-outline"}
              color={color}
              focused={focused}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="index"
        options={{
          title: "کتابخانه",
          tabBarIcon: ({ color, focused }) => (
            <TabIcon
              name={focused ? "library" : "library-outline"}
              color={color}
              focused={focused}
            />
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  settingsBtn: {
    marginLeft: 16,
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  iconWrap: {
    width: 44,
    height: 32,
    borderRadius: radii.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  iconWrapActive: {
    backgroundColor: colors.copperWash,
  },
});
