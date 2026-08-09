<template>
  <div id="app" class="app-container">
    <header class="app-header">
      <h1>🇷🇺 Napoleon — Russisch Vokabeltrainer</h1>
      <div class="header-info">
        <span class="level">A1–B1</span>
        <span class="word-count">{{ totalWords }} Wörter</span>
      </div>
    </header>

    <main class="app-main">
      <StatsDashboard 
        :today-count="todayCount"
        :correct-count="correctCount"
        :review-count="reviewCount"
        :streak="streak"
      />

      <CardTrainer 
        v-if="currentCardIndex < sessionKarten.length"
        :card="currentCard"
        :grammar="currentGrammar"
        :card-index="currentCardIndex"
        :total-cards="sessionKarten.length"
        @next-card="handleNextCard"
        @feedback="handleFeedback"
      />

      <div v-else class="completion-message">
        <h2>🎉 Glückwunsch!</h2>
        <p>Du hast alle {{ vocabList.length }} Wörter gelernt!</p>
        <button @click="resetTrainer" class="btn btn-primary">Nochmal!</button>
      </div>
    </main>

    <footer class="app-footer">
      <p>Napoleon © 2026</p>
      <button @click="lernstandZuruecksetzen" class="reset-btn">
        Lernstand zuruecksetzen
      </button>
      <button @click="lernstandZuruecksetzen" class="reset-btn">
        Lernstand zuruecksetzen
      </button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import CardTrainer from './components/CardTrainer.vue'
import StatsDashboard from './components/StatsDashboard.vue'
import { migriere, faelligeKarten, bewerte, speichereKarte, statistik,
         zuruecksetzen, type Card as SM2Card, type Bewertung } from './sm2'

interface VocabCard {
  id: string; word: string; stress: string; translation: string; phonetic: string
  word_type: string; category: string; level: string
}

interface GrammarData {
  id: string; word: string; word_type: string; explanation: string
  conjugation?: any; declension?: any; example_sentence: string; example_translation: string
  common_mistakes: string[]; tips_pronunciation: string; etymology: string
}

const vocabList = ref<VocabCard[]>([])
const grammarDb = ref<Map<string, GrammarData>>(new Map())
const currentCardIndex = ref(0)
const sessionKarten = ref<SM2Card[]>([])
const sm2Map = ref<Map<string, SM2Card>>(new Map())
const stats = ref({ gesamt: 0, neu: 0, faellig: 0, gelernt: 0 })
const todayCount = ref(0)
const correctCount = ref(0)
const reviewCount = ref(0)
const streak = ref(0)

const vocabMap = computed(() => {
  const m = new Map<string, VocabCard>()
  vocabList.value.forEach(v => m.set(v.id, v))
  return m
})
const currentCard = computed(() => {
  const k = sessionKarten.value[currentCardIndex.value]
  return k ? vocabMap.value.get(k.id) : undefined
})
const currentGrammar = computed(() => {
  if (!currentCard.value) return null
  return grammarDb.value.get(`${currentCard.value.id}_grammar`)
})
const totalWords = computed(() => vocabList.value.length)

onMounted(async () => {
  try {
    const vocabResponse = await fetch('/data/vocab_sm2.json')
    const vocabData = await vocabResponse.json()
    vocabList.value = Object.values(vocabData) as VocabCard[]

    const grammarResponse = await fetch('/data/grammar_db.json')
    const grammarData = await grammarResponse.json()
    Object.entries(grammarData).forEach(([key, value]) => {
      grammarDb.value.set(key, value as GrammarData)
    })

    console.log(`✅ Loaded ${vocabList.value.length} words`)
    loadStats()

    // SM-2: Karten anlegen (bestehende bleiben unberuehrt)
    const ids = vocabList.value.map(v => v.id)
    const mig = await migriere(ids)
    console.log(`SM-2: ${mig.neu} neu, ${mig.gesamt} gesamt`)
    await ladeSession()
  } catch (error) {
    console.error('Error:', error)
    alert('Fehler beim Laden der Vokabeln!')
  }
})

async function lernstandZuruecksetzen() {
  if (!confirm('Wirklich den gesamten Lernfortschritt loeschen?')) return
  await zuruecksetzen()
  const ids = vocabList.value.map(v => v.id)
  await migriere(ids)
  await ladeSession()
  todayCount.value = 0
  correctCount.value = 0
  streak.value = 0
  saveStats()
}

async function ladeSession() {
  sessionKarten.value = await faelligeKarten()
  sm2Map.value = new Map(sessionKarten.value.map(k => [k.id, k]))
  currentCardIndex.value = 0
  stats.value = await statistik()
  console.log(`Session: ${sessionKarten.value.length} Karten faellig`)
}

async function handleBewertung(b: Bewertung) {
  const aktuell = sessionKarten.value[currentCardIndex.value]
  if (!aktuell) return

  const aktualisiert = bewerte(aktuell, b)
  await speichereKarte(aktualisiert)

  todayCount.value++
  if (b === 'nochmal') {
    streak.value = 0
    sessionKarten.value.push(aktualisiert)
  } else {
    correctCount.value++
    streak.value++
  }

  currentCardIndex.value++
  stats.value = await statistik()
  saveStats()
}

function handleNextCard(isCorrect: boolean) {
  handleBewertung(isCorrect ? 'gut' : 'nochmal')
}

function handleFeedback() {}

async function resetTrainer() {
  await ladeSession()
  currentCardIndex.value = 0
  todayCount.value = 0
  correctCount.value = 0
  streak.value = 0
  saveStats()
}

function saveStats() {
  localStorage.setItem('trainer-stats', JSON.stringify({
    todayCount: todayCount.value,
    correctCount: correctCount.value,
    reviewCount: reviewCount.value,
    streak: streak.value,
    date: new Date().toISOString()
  }))
}

function loadStats() {
  const saved = localStorage.getItem('trainer-stats')
  if (saved) {
    const stats = JSON.parse(saved)
    const today = new Date().toDateString()
    const savedDate = new Date(stats.date).toDateString()
    if (today === savedDate) {
      todayCount.value = stats.todayCount
      correctCount.value = stats.correctCount
      reviewCount.value = stats.reviewCount
      streak.value = stats.streak
    }
  }
}
</script>

<style scoped>
:root {
  --primary: #6366F1;
  --success: #10B981;
  --bg: #FAFAF9;
  --text: #1F2937;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
}

.app-header {
  background: linear-gradient(135deg, var(--primary) 0%, #8B5CF6 100%);
  color: white;
  padding: 2rem;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.app-header h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
.header-info { display: flex; justify-content: center; gap: 2rem; opacity: 0.9; }
.level, .word-count { background: rgba(255, 255, 255, 0.2); padding: 0.3rem 0.8rem; border-radius: 20px; }

.app-main {
  flex: 1;
  max-width: 900px;
  margin: 2rem auto;
  width: 100%;
  padding: 0 1rem;
}

.completion-message {
  text-align: center;
  padding: 3rem;
  background: #F5F3FF;
  border-radius: 12px;
  border: 2px solid var(--success);
}

.completion-message h2 { font-size: 2rem; color: var(--success); margin-bottom: 1rem; }
.completion-message p { font-size: 1.1rem; color: #6B7280; margin-bottom: 2rem; }

.btn {
  padding: 0.8rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover {
  background: #5558E3;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.reset-btn {
  margin-top: 0.8rem;
  padding: 0.4rem 0.9rem;
  font-size: 0.75rem;
  background: transparent;
  color: #9CA3AF;
  border: 1px solid #4B5563;
  border-radius: 6px;
  cursor: pointer;
}

.reset-btn {
  margin-top: 0.8rem;
  padding: 0.4rem 0.9rem;
  font-size: 0.75rem;
  background: transparent;
  color: #9CA3AF;
  border: 1px solid #4B5563;
  border-radius: 6px;
  cursor: pointer;
}

.app-footer {
  background: var(--text);
  color: white;
  text-align: center;
  padding: 1.5rem;
  margin-top: 2rem;
}

@media (max-width: 768px) {
  .app-header h1 { font-size: 1.3rem; }
  .app-main { margin: 1rem auto; }
}
</style>
