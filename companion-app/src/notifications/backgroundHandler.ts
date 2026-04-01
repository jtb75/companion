import messaging from '@react-native-firebase/messaging'

export function registerBackgroundHandler() {
  messaging().setBackgroundMessageHandler(async (remoteMessage) => {
    console.log('[FCM] Background message received:', remoteMessage.messageId)
  })
}
