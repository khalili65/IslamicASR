import { View, StyleSheet, type ViewProps } from "react-native";
import { useColors } from "@/lib/useTheme";

export function Screen({ style, children, ...rest }: ViewProps) {
  const colors = useColors();
  return (
    <View
      style={[styles.root, { backgroundColor: colors.parchment }, style]}
      {...rest}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});
