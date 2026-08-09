<template>
  <div :class="['feedback-card', `score-${scoreCategory}`]">
    <div class="score-circle">
      <span class="score-text">{{ score }}%</span>
    </div>
    <div class="feedback-content">
      <p class="feedback-message">{{ feedback }}</p>
    </div>
    <div class="feedback-icon">
      <span v-if="score >= 80">⭐</span>
      <span v-else-if="score >= 60">👍</span>
      <span v-else>💪</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  feedback: string
  score: number
  tips?: string[]
}>()

const scoreCategory = computed(() => {
  if (props.score >= 80) return 'excellent'
  if (props.score >= 60) return 'good'
  return 'fair'
})
</script>

<style scoped>
.feedback-card { background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); display: flex; align-items: center; gap: 1.5rem; animation: slideUp 0.5s ease; }
.score-circle { position: relative; width: 100px; height: 100px; display: flex; align-items: center; justify-content: center; }
.score-text { font-size: 1.8rem; font-weight: 700; color: #1F2937; }
.feedback-content { flex: 1; }
.feedback-message { font-size: 1.1rem; color: #1F2937; margin: 0; }
.feedback-icon { font-size: 2rem; }
@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
