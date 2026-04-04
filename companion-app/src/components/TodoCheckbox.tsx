import React from 'react';
import { TouchableOpacity, StyleSheet, View } from 'react-native';
import { colors } from '../theme/colors';

interface TodoCheckboxProps {
  completed: boolean;
  onPress: () => void;
  size?: number;
}

export function TodoCheckbox({ completed, onPress, size = 22 }: TodoCheckboxProps) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      style={[
        styles.checkbox,
        { width: size, height: size, borderRadius: size / 4 },
        completed && styles.checked,
      ]}
    >
      {completed && <View style={[styles.inner, { width: size / 2, height: size / 2 }]} />}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  checkbox: {
    borderWidth: 2,
    borderColor: colors.gray300,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.white,
  },
  checked: {
    borderColor: colors.blue,
    backgroundColor: colors.blue,
  },
  inner: {
    backgroundColor: colors.white,
    borderRadius: 2,
  },
});
