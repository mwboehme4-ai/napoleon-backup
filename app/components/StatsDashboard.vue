<template>
  <div class="stats-dashboard">
    <div class="stats-grid">
      <div class="stat-card stat-today">
        <div class="stat-icon">📚</div>
        <div class="stat-content">
          <div class="stat-value">{{ todayCount }}</div>
          <div class="stat-label">Heute gelernt</div>
        </div>
      </div>
      <div class="stat-card stat-correct">
        <div class="stat-icon">✓</div>
        <div class="stat-content">
          <div class="stat-value">{{ correctCount }}</div>
          <div class="stat-label">Richtig</div>
        </div>
      </div>
      <div class="stat-card stat-streak">
        <div class="stat-icon">🔥</div>
        <div class="stat-content">
          <div class="stat-value">{{ streak }}</div>
          <div class="stat-label">Streak</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  todayCount: number
  correctCount: number
  reviewCount: number
  streak: number
}>()
</script>

<style scoped>
.stats-dashboard { display: flex; flex-direction: column; gap: 1.5rem; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; }
.stat-card { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); display: flex; align-items: center; gap: 1rem; border-top: 3px solid; }
.stat-icon { font-size: 2rem; }
.stat-value { font-size: 1.8rem; font-weight: 700; color: #1F2937; }
.stat-label { font-size: 0.85rem; color: #6B7280; margin-top: 0.3rem; }
.stat-today { border-top-color: #6366F1; }
.stat-correct { border-top-color: #10B981; }
.stat-streak { border-top-color: #EF4444; }
</style>
