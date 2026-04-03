import { useState } from 'react'
import auth from '@react-native-firebase/auth'
import { API_BASE } from '../api/client'

export interface ImageAnalysis {
  status: 'good' | 'poor' | 'error'
  feedback: string
  has_text: boolean
  brightness: number
}

export function useImageAnalysis() {
  const [analyzing, setAnalyzing] = useState(false)

  const analyzeImage = async (uri: string): Promise<ImageAnalysis | null> => {
    setAnalyzing(true)
    try {
      const user = auth().currentUser
      if (!user) return null

      const token = await user.getIdToken()
      
      const formData = new FormData()
      formData.append('file', {
        uri,
        type: 'image/jpeg',
        name: 'frame.jpg',
      } as any)

      const response = await fetch(`${API_BASE}/api/v1/documents/scan/analyze`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (!response.ok) return null
      
      const result = await response.json()
      return result as ImageAnalysis
    } catch (err) {
      console.log('[useImageAnalysis] error:', err)
      return null
    } finally {
      setAnalyzing(false)
    }
  }

  return { analyzeImage, analyzing }
}
