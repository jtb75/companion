import React, { useState } from 'react'
import {
  TouchableOpacity,
  StyleSheet,
  ActionSheetIOS,
  Platform,
  Alert,
  Text,
  View,
  ActivityIndicator,
} from 'react-native'
import { launchCamera, launchImageLibrary, Asset } from 'react-native-image-picker'
import auth from '@react-native-firebase/auth'
import { API_BASE } from '../api/client'
import { colors } from '../theme/colors'
import { useImageAnalysis } from '../hooks/useImageAnalysis'

type UploadStatus = 'idle' | 'analyzing' | 'uploading' | 'processing' | 'done' | 'error'

export function ScanButton() {
  const [status, setStatus] = useState<UploadStatus>('idle')
  const { analyzeImage } = useImageAnalysis()

  const handlePress = () => {
    if (Platform.OS === 'ios') {
      ActionSheetIOS.showActionSheetWithOptions(
        {
          options: ['Cancel', 'Take Photo', 'Choose from Library'],
          cancelButtonIndex: 0,
        },
        (buttonIndex) => {
          if (buttonIndex === 1) captureFromCamera()
          else if (buttonIndex === 2) pickFromLibrary()
        },
      )
    } else {
      // Android fallback using Alert
      Alert.alert('Scan Document', 'Choose an option', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Take Photo', onPress: captureFromCamera },
        { text: 'Choose from Library', onPress: pickFromLibrary },
      ])
    }
  }

  const captureFromCamera = async () => {
    try {
      const result = await launchCamera({
        mediaType: 'photo',
        quality: 0.8,
        maxWidth: 2048,
        maxHeight: 2048,
      })
      if (result.didCancel) return
      if (result.errorCode) {
        Alert.alert('Error', result.errorMessage || 'Could not open camera')
        return
      }
      const asset = result.assets?.[0]
      if (asset) handleAssetSelection(asset)
    } catch (err) {
      Alert.alert('Error', 'Failed to open camera')
    }
  }

  const pickFromLibrary = async () => {
    try {
      const result = await launchImageLibrary({
        mediaType: 'photo',
        quality: 0.8,
        maxWidth: 2048,
        maxHeight: 2048,
        selectionLimit: 1,
      })
      if (result.didCancel) return
      if (result.errorCode) {
        if (result.errorCode === 'permission') {
          Alert.alert(
            'Permission Required',
            'Please allow photo library access in Settings.',
          )
        } else {
          Alert.alert(
            'Error',
            result.errorMessage || 'Could not open photo library',
          )
        }
        return
      }
      const asset = result.assets?.[0]
      if (asset) handleAssetSelection(asset)
    } catch (err: any) {
      console.log('[ScanButton] library error:', err)
      Alert.alert('Error', err.message || 'Failed to open photo library')
    }
  }

  const handleAssetSelection = async (asset: Asset) => {
    if (!asset.uri) return

    setStatus('analyzing')
    const analysis = await analyzeImage(asset.uri)
    
    if (!analysis || analysis.status === 'error') {
      // Fallback: upload anyway if analysis fails
      uploadImage(asset)
      return
    }

    if (analysis.status === 'poor') {
      setStatus('idle')
      Alert.alert(
        'Scan Quality',
        analysis.feedback,
        [
          { text: 'Retake', style: 'cancel' },
          { text: 'Use Anyway', onPress: () => uploadImage(asset) }
        ]
      )
    } else {
      uploadImage(asset)
    }
  }

  const uploadImage = async (asset: Asset) => {
    if (!asset.uri) return

    setStatus('uploading')

    try {
      const user = auth().currentUser
      if (!user) {
        Alert.alert('Error', 'You must be signed in to scan documents')
        setStatus('idle')
        return
      }

      const token = await user.getIdToken()

      const formData = new FormData()
      formData.append('file', {
        uri: asset.uri,
        type: asset.type || 'image/jpeg',
        name: asset.fileName || 'scan.jpg',
      } as any)

      setStatus('uploading')

      const response = await fetch(`${API_BASE}/api/v1/documents/scan`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`)
      }

      setStatus('processing')

      // Brief delay to show processing state before done
      setTimeout(() => {
        setStatus('done')
        Alert.alert('Success', "Document uploaded! We'll notify you when it's processed.")
        setTimeout(() => setStatus('idle'), 2000)
      }, 1000)
    } catch (err) {
      setStatus('error')
      Alert.alert('Upload Failed', 'Could not upload the document. Please try again.')
      setTimeout(() => setStatus('idle'), 2000)
    }
  }

  const statusLabel: Record<UploadStatus, string> = {
    idle: '',
    analyzing: 'Analyzing...',
    uploading: 'Uploading...',
    processing: 'Processing...',
    done: 'Done!',
    error: 'Failed',
  }

  return (
    <View style={styles.wrapper} pointerEvents="box-none">
      {status !== 'idle' && (
        <View style={styles.statusBadge}>
          {(status === 'analyzing' || status === 'uploading' || status === 'processing') && (
            <ActivityIndicator size="small" color={colors.white} style={{ marginRight: 6 }} />
          )}
          <Text style={styles.statusText}>{statusLabel[status]}</Text>
        </View>
      )}
      <TouchableOpacity
        style={[styles.fab, status !== 'idle' && status !== 'done' && styles.fabDisabled]}
        onPress={handlePress}
        disabled={status === 'analyzing' || status === 'uploading' || status === 'processing'}
        activeOpacity={0.7}
      >
        <Text style={styles.fabIcon}>📷</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: {
    position: 'absolute',
    bottom: 24,
    right: 20,
    alignItems: 'flex-end',
  },
  fab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.blue,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.2,
    shadowRadius: 5,
    elevation: 6,
  },
  fabDisabled: {
    opacity: 0.6,
  },
  fabIcon: {
    fontSize: 24,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.gray800,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginBottom: 8,
  },
  statusText: {
    color: colors.white,
    fontSize: 13,
    fontWeight: '600',
  },
})
