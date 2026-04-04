import { useEffect, useState } from 'react'
import { Alert, Platform } from 'react-native'
import messaging from '@react-native-firebase/messaging'
import { api } from '../api/client'

export function usePushNotifications(isAuthenticated: boolean) {
  const [permissionGranted, setPermissionGranted] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) return

    let unsubscribeRefresh: (() => void) | undefined
    let unsubscribeMessage: (() => void) | undefined

    const setup = async () => {
      // Request permission
      const authStatus = await messaging().requestPermission()
      const granted =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL
      setPermissionGranted(granted)
      console.log('[usePushNotifications] permission:', authStatus, 'granted:', granted)

      if (!granted) {
        console.log('[usePushNotifications] permission not granted, skipping')
        return
      }

      // Register for remote messages (required on iOS before getToken)
      if (!messaging().isDeviceRegisteredForRemoteMessages) {
        await messaging().registerDeviceForRemoteMessages()
      }

      // Get and register FCM token
      console.log('[usePushNotifications] getting FCM token...')
      const token = await messaging().getToken()
      console.log('[usePushNotifications] FCM token:', token ? `${token.substring(0, 20)}...` : 'null')
      await registerToken(token)

      // Listen for token refresh
      unsubscribeRefresh = messaging().onTokenRefresh(async (newToken) => {
        await registerToken(newToken)
      })

      // Foreground message handler
      unsubscribeMessage = messaging().onMessage(async (remoteMessage) => {
        Alert.alert(
          remoteMessage.notification?.title || 'New Notification',
          remoteMessage.notification?.body || '',
        )
      })
    }

    setup().catch((err) => {
      console.log('[usePushNotifications] setup error:', err)
    })

    return () => {
      unsubscribeRefresh?.()
      unsubscribeMessage?.()
    }
  }, [isAuthenticated])

  return { permissionGranted }
}

async function registerToken(token: string) {
  try {
    await api('/api/v1/me/devices', {
      method: 'POST',
      body: JSON.stringify({
        fcm_token: token,
        platform: Platform.OS,
      }),
    })
  } catch (err) {
    console.log('[usePushNotifications] failed to register token:', err)
  }
}
