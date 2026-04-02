import React, { useEffect, useRef, useState, useCallback } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native'
import { useRoute } from '@react-navigation/native'
import { api } from '../api/client'
import { colors, brand } from '../theme/colors'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function ChatScreen() {
  const route = useRoute<any>()
  const reviewId = route.params?.reviewId as string | undefined
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const [sending, setSending] = useState(false)
  const [starting, setStarting] = useState(true)
  const flatListRef = useRef<FlatList>(null)

  useEffect(() => {
    startSession()
  }, [reviewId])

  const startSession = async () => {
    // Determine trigger based on navigation context
    const trigger = reviewId ? 'document_review' : 'user_initiated'

    // Show instant greeting, then connect in background
    setMessages([{
      id: '0',
      role: 'assistant',
      content: reviewId
        ? `Let me pull up that document for you...`
        : `Hi! I'm ${brand.short}. What would you like to do today?`,
    }])
    setStarting(false)

    try {
      const res = await api<{ session_id: string; greeting: string }>(
        '/api/v1/conversation/start',
        { method: 'POST', body: JSON.stringify({ initial_context: trigger }) },
      )
      setSessionId(res.session_id)
      sessionIdRef.current = res.session_id
      // Update greeting with LLM-generated one if different
      if (res.greeting) {
        setMessages([{ id: '0', role: 'assistant', content: res.greeting }])
      }
    } catch {
      // Keep the static greeting, just log the error
      console.log('[ChatScreen] Failed to start session')
    }
  }

  const sendMessage = useCallback(async () => {
    if (!input.trim() || sending) return
    if (!sessionIdRef.current) {
      await startSession()
      if (!sessionIdRef.current) return
    }
    const text = input.trim()
    setInput('')

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
    }
    setMessages((prev) => [...prev, userMsg])
    setSending(true)

    try {
      const res = await api<{ response: string }>(
        '/api/v1/conversation/message',
        {
          method: 'POST',
          body: JSON.stringify({ text }),
        },
      )
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: res.response,
        },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: "Sorry, I couldn't process that. Try again?",
        },
      ])
    } finally {
      setSending(false)
    }
  }, [input, sessionId, sending])

  if (starting) {
    return (
      <View style={styles.center}>
        <Text style={styles.emoji}>{brand.emoji}</Text>
        <ActivityIndicator size="large" color={colors.blue} />
        <Text style={styles.connectingText}>Connecting to {brand.short}...</Text>
      </View>
    )
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(m) => m.id}
        contentContainerStyle={styles.messageList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        renderItem={({ item }) => (
          <View style={[styles.bubble, item.role === 'user' ? styles.userBubble : styles.assistantBubble]}>
            {item.role === 'assistant' && <Text style={styles.botName}>{brand.short}</Text>}
            <Text style={[styles.bubbleText, item.role === 'user' && styles.userText]}>{item.content}</Text>
          </View>
        )}
      />

      {sending && (
        <View style={styles.typingRow}>
          <ActivityIndicator size="small" color={colors.gray400} />
          <Text style={styles.typingText}>{brand.short} is thinking...</Text>
        </View>
      )}

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder={`Ask ${brand.short} anything...`}
          placeholderTextColor={colors.gray400}
          returnKeyType="send"
          onSubmitEditing={sendMessage}
          editable={!sending}
        />
        <TouchableOpacity
          style={[styles.sendButton, (!input.trim() || sending) && styles.sendDisabled]}
          onPress={sendMessage}
          disabled={!input.trim() || sending}
        >
          <Text style={styles.sendText}>Send</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.cream, gap: 12 },
  emoji: { fontSize: 36 },
  connectingText: { fontSize: 14, color: colors.gray500 },
  messageList: { padding: 16, paddingBottom: 8 },
  bubble: { maxWidth: '80%', borderRadius: 16, padding: 12, marginBottom: 8 },
  userBubble: { alignSelf: 'flex-end', backgroundColor: colors.blue },
  assistantBubble: { alignSelf: 'flex-start', backgroundColor: colors.white, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 1 },
  botName: { fontSize: 11, fontWeight: '700', color: colors.blue, marginBottom: 4 },
  bubbleText: { fontSize: 15, lineHeight: 22, color: colors.gray800 },
  userText: { color: colors.white },
  typingRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 20, paddingBottom: 4 },
  typingText: { fontSize: 13, color: colors.gray400 },
  inputRow: { flexDirection: 'row', padding: 12, paddingBottom: Platform.OS === 'ios' ? 28 : 12, backgroundColor: colors.white, borderTopWidth: 1, borderTopColor: colors.gray200, gap: 8 },
  input: { flex: 1, backgroundColor: colors.gray50, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, fontSize: 15, color: colors.gray800 },
  sendButton: { backgroundColor: colors.blue, borderRadius: 20, paddingHorizontal: 20, justifyContent: 'center' },
  sendDisabled: { opacity: 0.5 },
  sendText: { color: colors.white, fontWeight: '600', fontSize: 15 },
})
