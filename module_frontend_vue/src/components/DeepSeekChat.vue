<template>
  <div class="chat-box">
    <div class="title">AI 导购</div>
    <div class="input-row">
      <input v-model="text" placeholder="请输入需求，如：通勤黑色外套" @keyup.enter="send" />
      <button :disabled="loading" @click="send">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const text = ref('')
const props = defineProps({ loading: Boolean })
const emit = defineEmits(['send'])
const send = () => {
  emit('send', text.value)
}
</script>

<style scoped>
.chat-box { background: #111827; border: 1px solid #334155; border-radius: 12px; padding: 12px; }
.title { font-weight: 700; margin-bottom: 8px; }
.input-row { display: flex; gap: 8px; }
input { flex: 1; background: #0b1220; border: 1px solid #334155; color: #e2e8f0; border-radius: 8px; padding: 8px; }
button { background: #2563eb; border: none; color: white; border-radius: 8px; padding: 8px 12px; }
</style>
