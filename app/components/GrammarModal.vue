<template>
  <div class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>📖 {{ grammar.word }}</h2>
        <button @click="closeModal" class="close-btn">✕</button>
      </div>
      <div class="explanation">
        <p>{{ grammar.explanation }}</p>
      </div>
      <div class="tips-section">
        <div v-if="grammar.tips_pronunciation" class="tip-box">
          <h4>🔊 Aussprache-Tipps</h4>
          <p>{{ grammar.tips_pronunciation }}</p>
        </div>
        <div v-if="grammar.etymology" class="tip-box">
          <h4>📚 Herkunft</h4>
          <p>{{ grammar.etymology }}</p>
        </div>
      </div>
      <div v-if="grammar.common_mistakes?.length" class="mistakes-section">
        <h3>⚠️ Häufige Fehler</h3>
        <ul class="mistakes-list">
          <li v-for="(mistake, idx) in grammar.common_mistakes" :key="idx">{{ mistake }}</li>
        </ul>
      </div>
      <button @click="closeModal" class="btn btn-primary">Schließen</button>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Grammar {
  word: string; word_type: string; explanation: string
  conjugation?: any; declension?: any
  common_mistakes: string[]; tips_pronunciation: string; etymology: string
  example_sentence: string; example_translation: string
}

const props = defineProps<{ grammar: Grammar }>()
const emit = defineEmits<{ 'close': [] }>()

function closeModal() {
  emit('close')
}
</script>

<style scoped>
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.modal-content { background: white; border-radius: 12px; max-width: 700px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
.modal-header { background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); color: white; padding: 1.5rem; display: flex; justify-content: space-between; border-radius: 12px 12px 0 0; }
.modal-header h2 { margin: 0; }
.close-btn { background: rgba(255, 255, 255, 0.2); border: none; color: white; font-size: 1.5rem; cursor: pointer; width: 40px; height: 40px; border-radius: 50%; }
.explanation { padding: 1.5rem; background: #F3F4F6; border-bottom: 1px solid #E5E7EB; }
.tips-section { padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
.tip-box { background: #ECFDF5; padding: 1rem; border-left: 4px solid #10B981; border-radius: 8px; }
.tip-box h4 { margin-top: 0; color: #065F46; }
.mistakes-section { padding: 1.5rem; background: #FEF2F2; border-left: 4px solid #EF4444; }
.mistakes-list { list-style: none; padding: 0; }
.mistakes-list li { padding: 0.5rem 0; color: #7F1D1D; }
.btn { width: 100%; padding: 1rem; margin: 1.5rem; background: #6366F1; color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }
</style>
