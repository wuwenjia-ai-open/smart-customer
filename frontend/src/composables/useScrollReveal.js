import { onMounted, onUnmounted } from 'vue'

export function useScrollReveal(selector = '[data-reveal]', threshold = 0.15) {
  let io = null

  function observeAll() {
    if (!io) return
    document.querySelectorAll(selector).forEach(el => {
      if (!el.classList.contains('is-revealed')) io.observe(el)
    })
  }

  onMounted(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      document.querySelectorAll(selector).forEach(el => el.classList.add('is-revealed'))
      return
    }
    io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('is-revealed')
          io.unobserve(e.target)
        }
      })
    }, { threshold, rootMargin: '0px 0px -50px 0px' })

    observeAll()
  })

  onUnmounted(() => {
    io?.disconnect()
    io = null
  })

  return { observeAll }
}
