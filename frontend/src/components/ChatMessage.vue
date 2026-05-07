<template>
  <div :class="['c-msg', msg.role]">
    <div class="c-av">{{ msg.role === 'assistant' ? '犀' : userInitial }}</div>
    <div class="c-body">
      <template v-if="msg.typing">
        <span class="thinking-text">{{ msg.content || '' }}</span>
        <span class="typing-dots"><i>.</i><i>.</i><i>.</i></span>
      </template>
      <div v-else v-html="msg.content"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  msg: Object,
  userInitial: String,
})
</script>
