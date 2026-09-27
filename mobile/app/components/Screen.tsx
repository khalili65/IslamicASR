import { View, StyleSheet, type ViewProps } from "react-native";
import { colors } from "@/constants/theme";

export function Screen({ style, children, ...rest }: ViewProps) {
  return (
    <View style={[styles.root, style]} {...rest}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.parchment,
  },
});
