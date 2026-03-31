import React from 'react'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { NavigationContainer } from '@react-navigation/native'
import { Text } from 'react-native'
import { TodayScreen } from '../screens/TodayScreen'
import { ChatScreen } from '../screens/ChatScreen'
import { MyStuffScreen } from '../screens/MyStuffScreen'
import { ProfileScreen } from '../screens/ProfileScreen'
import { LoginScreen } from '../auth/LoginScreen'
import { useAuth } from '../auth/AuthProvider'
import { colors } from '../theme/colors'

const Tab = createBottomTabNavigator()

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  const icons: Record<string, string> = {
    Today: '🏠',
    Chat: '💬',
    'My Stuff': '📋',
    Profile: '👤',
  }
  return (
    <Text style={{ fontSize: focused ? 22 : 20, opacity: focused ? 1 : 0.5 }}>
      {icons[label] || '•'}
    </Text>
  )
}

export function AppNavigator() {
  const { user, loading } = useAuth()

  if (loading) return null

  return (
    <NavigationContainer>
      {user ? (
        <Tab.Navigator
          screenOptions={({ route }) => ({
            tabBarIcon: ({ focused }) => <TabIcon label={route.name} focused={focused} />,
            tabBarActiveTintColor: colors.blue,
            tabBarInactiveTintColor: colors.gray400,
            tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
            tabBarStyle: { paddingTop: 4, height: 84 },
            headerStyle: { backgroundColor: colors.white },
            headerTitleStyle: { fontWeight: '700', color: colors.gray900 },
          })}
        >
          <Tab.Screen name="Today" component={TodayScreen} />
          <Tab.Screen
            name="Chat"
            component={ChatScreen}
            options={{ title: 'D.D.' }}
          />
          <Tab.Screen name="My Stuff" component={MyStuffScreen} />
          <Tab.Screen name="Profile" component={ProfileScreen} />
        </Tab.Navigator>
      ) : (
        <LoginScreen />
      )}
    </NavigationContainer>
  )
}
