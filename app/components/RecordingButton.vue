<template>
  <div class="recording-container">
    <button @click="toggleRecording" :class="['recording-button', { recording: isRecording }]">
      {{ recordingText }}
    </button>
    <span v-if="isRecording" class="timer">{{ recordingTime }}s</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Feedback {
  score: number
  message: string
  tips: string[]
}

const props = defineProps<{
  word: string
  stress: string
}>()

const emit = defineEmits<{
  'feedback': [feedback: Feedback]
}>()

const isRecording = ref(false)
const recordingTime = ref(0)

const recordingText = computed(() => {
  return isRecording.value ? 'Stopp' : '🎤 Sprich jetzt!'
})

function toggleRecording() {
  isRecording.value = !isRecording.value
  if (isRecording.value) {
    recordingTime.value = 0
    const interval = setInterval(() => {
      recordingTime.value++
      if (recordingTime.value >= 10) {
        isRecording.value = false
        clearInterval(interval)
        submitFeedback(true)
      }
    }, 1000)
  }
}

function submitFeedback(isCorrect: boolean) {
  const feedback: Feedback = isCorrect ? {
    score: 85,
    message: 'Gut gesprochen! Deine Aussprache ist verständlich.',
    tips: []
  } : {
    score: 60,
    message: 'Nicht schlecht! Versuch es nochmal.',
    tips: ['Höre das Wort mehrmals an', 'Sprich langsam']
  }
  emit('feedback', feedback)
}
</script>

<style scoped>
.recording-container { display: flex; align-items: center; gap: 1rem; justify-content: center; }
.recording-button { padding: 1rem 2rem; font-size: 1.1rem; font-weight: 600; border: none; border-radius: 8px; cursor: pointer; background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); color: white; transition: all 0.3s ease; }
.recording-button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }
.recording-button.recording { background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); animation: pulse 1.5s ease-in-out infinite; }
.timer { font-size: 1.2rem; font-weight: 600; color: #EF4444; }
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
}
</style>
