<template>
  <div class="card-trainer">
    <div class="card-container">
      <div class="card-header">
        <span class="card-index">{{ cardIndex + 1 }} / {{ totalCards }}</span>
        <span class="progress-bar">
          <span class="progress-fill" :style="{ width: `${(cardIndex / totalCards) * 100}%` }"></span>
        </span>
      </div>

      <div class="word-card">
        <div class="word-display">
          <div class="stress-indicator">
            <span class="word-text">{{ card.stress }}</span>
          </div>
          <div class="phonetic">{{ card.phonetic }}</div>
        </div>
        <div class="translation">{{ card.translation }}</div>
        <div class="badges">
          <span :class="`badge badge-${card.word_type}`">
            {{ getWordTypeLabel(card.word_type) }}
          </span>
          <span class="badge badge-level">{{ card.level }}</span>
        </div>
      </div>

      <div class="card-controls">
        <button @click="playAudio" class="btn btn-secondary" :disabled="isPlayingAudio">
          🔊 {{ isPlayingAudio ? 'Abspielen...' : 'Aussprechen' }}
        </button>
        <button @click="showGrammarModal = true" class="btn btn-secondary">
          📖 Grammatik
        </button>
      </div>
    </div>

    <div class="recording-section">
      <h3>Sprich das Wort:</h3>
      <RecordingButton :word="card.word" :stress="card.stress" @feedback="handleFeedback" />
    </div>

    <FeedbackCard v-if="lastFeedback" :feedback="lastFeedback" :score="lastScore" />

    <div class="navigation">
      <button @click="skipCard" class="btn btn-outline">↻ Überspringen</button>
      <button @click="nextCard(false)" class="btn btn-outline">✗ Falsch</button>
      <button @click="nextCard(true)" class="btn btn-success">✓ Richtig</button>
    </div>

    <GrammarModal v-if="showGrammarModal && grammar" :grammar="grammar" @close="showGrammarModal = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import RecordingButton from './RecordingButton.vue'
import FeedbackCard from './FeedbackCard.vue'
import GrammarModal from './GrammarModal.vue'

interface Card {
  id: string; word: string; stress: string; translation: string; phonetic: string
  word_type: string; category: string; level: string
}

interface Grammar {
  word: string; word_type: string; explanation: string
  conjugation?: any; declension?: any; example_sentence: string; example_translation: string
  common_mistakes: string[]; tips_pronunciation: string; etymology: string
}

interface Feedback {
  score: number; message: string; tips: string[]
}

const props = defineProps<{
  card: Card
  grammar: Grammar | null
  cardIndex: number
  totalCards: number
}>()

const emit = defineEmits<{
  'next-card': [isCorrect: boolean]
  'feedback': [feedback: Feedback]
}>()

const showGrammarModal = ref(false)
const isPlayingAudio = ref(false)
const lastFeedback = ref<string | null>(null)
const lastScore = ref(0)

const ruVoices = ref<SpeechSynthesisVoice[]>([])
const selectedVoice = ref<string>('')

function ladeStimmen() {
  const alle = speechSynthesis.getVoices()
  ruVoices.value = alle.filter(v => v.lang.toLowerCase().startsWith('ru'))
  if (!selectedVoice.value && ruVoices.value.length) {
    const ruslan = ruVoices.value.find(v => /ruslan/i.test(v.name))
    selectedVoice.value = (ruslan || ruVoices.value[0]).name
  }
  console.log('Russische Stimmen:', ruVoices.value.map(v => v.name))
}

ladeStimmen()
speechSynthesis.onvoiceschanged = ladeStimmen

async function playAudio() {
  isPlayingAudio.value = true
  try {
    if (!('speechSynthesis' in window)) {
      isPlayingAudio.value = false
      return
    }
    const utterance = new SpeechSynthesisUtterance(props.card.word)
    utterance.lang = 'ru-RU'
    utterance.rate = 0.9

    const stimme = ruVoices.value.find(v => v.name === selectedVoice.value)
    if (stimme) utterance.voice = stimme

    utterance.onend = () => { isPlayingAudio.value = false }
    utterance.onerror = () => { isPlayingAudio.value = false }

    speechSynthesis.cancel()
    speechSynthesis.speak(utterance)
  } catch (e) {
    console.error('Audio-Fehler:', e)
    isPlayingAudio.value = false
  }
}

function getWordTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    'verb': 'Verb', 'noun': 'Nomen', 'adjective': 'Adjektiv', 'adverb': 'Adverb'
  }
  return labels[type] || type
}

function handleFeedback(feedback: Feedback) {
  lastFeedback.value = feedback.message
  lastScore.value = feedback.score
  emit('feedback', feedback)
}

function skipCard() {
  lastFeedback.value = null
  emit('next-card', false)
}

function nextCard(isCorrect: boolean) {
  lastFeedback.value = null
  emit('next-card', isCorrect)
}
</script>

<style scoped>
.card-trainer { display: flex; flex-direction: column; gap: 2rem; animation: fadeIn 0.3s ease; }
.card-container { background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
.card-header { background: linear-gradient(90deg, #6366F1 0%, #8B5CF6 100%); padding: 1rem; color: white; display: flex; align-items: center; gap: 1rem; }
.card-index { font-weight: 600; font-size: 0.9rem; min-width: 60px; }
.progress-bar { flex: 1; height: 4px; background: rgba(255, 255, 255, 0.3); border-radius: 2px; overflow: hidden; }
.progress-fill { display: block; height: 100%; background: #10B981; transition: width 0.3s ease; }
.word-card { padding: 3rem 2rem; text-align: center; }
.word-text { font-size: 2.5rem; font-weight: 700; color: #1F2937; }
.phonetic { font-size: 1rem; color: #6B7280; margin-top: 0.5rem; }
.translation { font-size: 1.3rem; color: #374151; margin: 1.5rem 0; }
.badges { display: flex; justify-content: center; gap: 0.8rem; flex-wrap: wrap; }
.badge { padding: 0.4rem 0.8rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
.badge-verb { background: #DBEAFE; color: #1E40AF; }
.badge-noun { background: #DCFCE7; color: #166534; }
.badge-adjective { background: #FED7AA; color: #92400E; }
.badge-level { background: #F3E8FF; color: #6B21A8; }
.card-controls { padding: 1.5rem 2rem; display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; border-top: 1px solid #E5E7EB; }
.btn { padding: 0.8rem 1.5rem; border: none; border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease; }
.btn-secondary { background: #F3F4F6; color: #1F2937; border: 1px solid #D1D5DB; }
.btn-secondary:hover:not(:disabled) { background: #E5E7EB; }
.voice-select {
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  border: 1px solid #D1D5DB;
  background: #F3F4F6;
  font-size: 0.85rem;
  max-width: 180px;
}

.recording-section { background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
.navigation { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }
.btn-outline { background: white; color: #6B7280; border: 2px solid #D1D5DB; }
.btn-success { background: #10B981; color: white; border: none; }
</style>
