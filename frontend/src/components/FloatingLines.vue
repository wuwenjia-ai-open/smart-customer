<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Mesh, OrthographicCamera, PlaneGeometry, Scene, ShaderMaterial, Vector2, Vector3, WebGLRenderer } from 'three'

const props = defineProps({
  linesGradient: { type: Array, default: () => ['#3B82F6', '#8B5CF6', '#06B6D4'] },
  enabledWaves: { type: Array, default: () => ['top', 'middle', 'bottom'] },
  lineCount: { type: [Number, Array], default: () => [6] },
  lineDistance: { type: [Number, Array], default: () => [5] },
  topWavePosition: { type: Object, default: () => ({ x: 10, y: 0.5, rotate: -0.4 }) },
  middleWavePosition: { type: Object, default: () => ({ x: 5, y: 0, rotate: 0.2 }) },
  bottomWavePosition: { type: Object, default: () => ({ x: 2, y: -0.7, rotate: 0.4 }) },
  animationSpeed: { type: Number, default: 1 },
  interactive: { type: Boolean, default: true },
  bendRadius: { type: Number, default: 5 },
  bendStrength: { type: Number, default: -0.5 },
  mouseDamping: { type: Number, default: 0.05 },
  parallax: { type: Boolean, default: true },
  parallaxStrength: { type: Number, default: 0.2 },
})

const containerRef = ref(null)

const MAX_GRADIENT_STOPS = 8

const vertexShader = `
precision highp float;
void main() {
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`

const fragmentShader = `
precision highp float;
uniform float iTime;
uniform vec3 iResolution;
uniform float animationSpeed;
uniform bool enableTop, enableMiddle, enableBottom;
uniform int topLineCount, middleLineCount, bottomLineCount;
uniform float topLineDistance, middleLineDistance, bottomLineDistance;
uniform vec3 topWavePosition, middleWavePosition, bottomWavePosition;
uniform vec2 iMouse;
uniform bool interactive;
uniform float bendRadius, bendStrength, bendInfluence;
uniform bool parallax;
uniform float parallaxStrength;
uniform vec2 parallaxOffset;
uniform vec3 lineGradient[8];
uniform int lineGradientCount;

const vec3 BLACK = vec3(0.02, 0.02, 0.03);
const vec3 PINK  = vec3(233.0, 71.0, 245.0) / 255.0;
const vec3 BLUE  = vec3(47.0, 75.0, 162.0) / 255.0;

mat2 rotate(float r) {
  return mat2(cos(r), sin(r), -sin(r), cos(r));
}

vec3 background_color(vec2 uv) {
  vec3 col = vec3(0.0);
  float y = sin(uv.x - 0.2) * 0.3 - 0.1;
  float m = uv.y - y;
  col += mix(BLUE, BLACK, smoothstep(0.0, 1.0, abs(m)));
  col += mix(PINK, BLACK, smoothstep(0.0, 1.0, abs(m - 0.8)));
  return col * 0.5;
}

vec3 getLineColor(float t, vec3 baseColor) {
  if (lineGradientCount <= 0) return baseColor;
  vec3 gradientColor;
  if (lineGradientCount == 1) {
    gradientColor = lineGradient[0];
  } else {
    float clampedT = clamp(t, 0.0, 0.9999);
    float scaled = clampedT * float(lineGradientCount - 1);
    int idx = int(floor(scaled));
    float f = fract(scaled);
    int idx2 = min(idx + 1, lineGradientCount - 1);
    vec3 c1 = lineGradient[idx];
    vec3 c2 = lineGradient[idx2];
    gradientColor = mix(c1, c2, f);
  }
  return gradientColor;
}

float wave(vec2 uv, float offset, vec2 screenUv, vec2 mouseUv, bool shouldBend) {
  float time = iTime * animationSpeed;
  float x_offset = offset;
  float x_movement = time * 0.1;
  float amp = sin(offset + time * 0.2) * 0.3;
  float y = sin(uv.x + x_offset + x_movement) * amp;
  if (shouldBend) {
    vec2 d = screenUv - mouseUv;
    float influence = exp(-dot(d, d) * bendRadius);
    float bendOffset = (mouseUv.y - screenUv.y) * influence * bendStrength * bendInfluence;
    y += bendOffset;
  }
  float m = uv.y - y;
  return 0.0175 / max(abs(m) + 0.01, 1e-3) + 0.01;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
  vec2 baseUv = (2.0 * fragCoord - iResolution.xy) / iResolution.y;
  baseUv.y *= -1.0;
  if (parallax) baseUv += parallaxOffset;
  vec3 col = vec3(0.0);
  vec3 b = lineGradientCount > 0 ? vec3(0.0) : background_color(baseUv);
  vec2 mouseUv = vec2(0.0);
  if (interactive) {
    mouseUv = (2.0 * iMouse - iResolution.xy) / iResolution.y;
    mouseUv.y *= -1.0;
  }
  if (enableBottom) {
    for (int i = 0; i < bottomLineCount; ++i) {
      float fi = float(i);
      float t = fi / max(float(bottomLineCount - 1), 1.0);
      vec3 lineCol = getLineColor(t, b);
      float angle = bottomWavePosition.z * log(length(baseUv) + 1.0);
      vec2 ruv = baseUv * rotate(angle);
      col += lineCol * wave(ruv + vec2(bottomLineDistance * fi + bottomWavePosition.x, bottomWavePosition.y), 1.5 + 0.2 * fi, baseUv, mouseUv, interactive) * 0.2;
    }
  }
  if (enableMiddle) {
    for (int i = 0; i < middleLineCount; ++i) {
      float fi = float(i);
      float t = fi / max(float(middleLineCount - 1), 1.0);
      vec3 lineCol = getLineColor(t, b);
      float angle = middleWavePosition.z * log(length(baseUv) + 1.0);
      vec2 ruv = baseUv * rotate(angle);
      col += lineCol * wave(ruv + vec2(middleLineDistance * fi + middleWavePosition.x, middleWavePosition.y), 2.0 + 0.15 * fi, baseUv, mouseUv, interactive);
    }
  }
  if (enableTop) {
    for (int i = 0; i < topLineCount; ++i) {
      float fi = float(i);
      float t = fi / max(float(topLineCount - 1), 1.0);
      vec3 lineCol = getLineColor(t, b);
      float angle = topWavePosition.z * log(length(baseUv) + 1.0);
      vec2 ruv = baseUv * rotate(angle);
      ruv.x *= -1.0;
      col += lineCol * wave(ruv + vec2(topLineDistance * fi + topWavePosition.x, topWavePosition.y), 1.0 + 0.2 * fi, baseUv, mouseUv, interactive) * 0.1;
    }
  }
  fragColor = vec4(col, 1.0);
}

void main() {
  vec4 color = vec4(0.0);
  mainImage(color, gl_FragCoord.xy);
  gl_FragColor = color;
}`

function hexToVec3(hex) {
  let value = hex.trim()
  if (value.startsWith('#')) value = value.slice(1)
  let r = 255, g = 255, b = 255
  if (value.length === 3) {
    r = parseInt(value[0] + value[0], 16); g = parseInt(value[1] + value[1], 16); b = parseInt(value[2] + value[2], 16)
  } else if (value.length === 6) {
    r = parseInt(value.slice(0, 2), 16); g = parseInt(value.slice(2, 4), 16); b = parseInt(value.slice(4, 6), 16)
  }
  return new Vector3(r / 255, g / 255, b / 255)
}

const getLineCount = (waveType) => {
  if (typeof props.lineCount === 'number') return props.lineCount
  if (!props.enabledWaves.includes(waveType)) return 0
  const idx = props.enabledWaves.indexOf(waveType)
  return props.lineCount[idx] ?? 6
}

const getLineDistance = (waveType) => {
  if (typeof props.lineDistance === 'number') return props.lineDistance * 0.01
  if (!props.enabledWaves.includes(waveType)) return 0.01
  const idx = props.enabledWaves.indexOf(waveType)
  return (props.lineDistance[idx] ?? 0.1) * 0.01
}

let cleanup = null

function setupScene() {
  if (!containerRef.value) return
  let active = true
  const container = containerRef.value
  container.innerHTML = ''

  const scene = new Scene()
  const camera = new OrthographicCamera(-1, 1, 1, -1, 0, 1)
  camera.position.z = 1

  const renderer = new WebGLRenderer({ antialias: true, alpha: false })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.domElement.style.width = '100%'
  renderer.domElement.style.height = '100%'
  container.appendChild(renderer.domElement)

  const uniforms = {
    iTime: { value: 0 },
    iResolution: { value: new Vector3(1, 1, 1) },
    animationSpeed: { value: props.animationSpeed },
    enableTop: { value: props.enabledWaves.includes('top') },
    enableMiddle: { value: props.enabledWaves.includes('middle') },
    enableBottom: { value: props.enabledWaves.includes('bottom') },
    topLineCount: { value: getLineCount('top') },
    middleLineCount: { value: getLineCount('middle') },
    bottomLineCount: { value: getLineCount('bottom') },
    topLineDistance: { value: getLineDistance('top') },
    middleLineDistance: { value: getLineDistance('middle') },
    bottomLineDistance: { value: getLineDistance('bottom') },
    topWavePosition: { value: new Vector3(props.topWavePosition?.x ?? 10, props.topWavePosition?.y ?? 0.5, props.topWavePosition?.rotate ?? -0.4) },
    middleWavePosition: { value: new Vector3(props.middleWavePosition?.x ?? 5, props.middleWavePosition?.y ?? 0, props.middleWavePosition?.rotate ?? 0.2) },
    bottomWavePosition: { value: new Vector3(props.bottomWavePosition?.x ?? 2, props.bottomWavePosition?.y ?? -0.7, props.bottomWavePosition?.rotate ?? 0.4) },
    iMouse: { value: new Vector2(-1000, -1000) },
    interactive: { value: props.interactive },
    bendRadius: { value: props.bendRadius },
    bendStrength: { value: props.bendStrength },
    bendInfluence: { value: 0 },
    parallax: { value: props.parallax },
    parallaxStrength: { value: props.parallaxStrength },
    parallaxOffset: { value: new Vector2(0, 0) },
    lineGradient: { value: Array.from({ length: MAX_GRADIENT_STOPS }, () => new Vector3(1, 1, 1)) },
    lineGradientCount: { value: 0 },
  }

  if (props.linesGradient && props.linesGradient.length > 0) {
    const stops = props.linesGradient.slice(0, MAX_GRADIENT_STOPS)
    uniforms.lineGradientCount.value = stops.length
    stops.forEach((hex, i) => { const c = hexToVec3(hex); uniforms.lineGradient.value[i].set(c.x, c.y, c.z) })
  }

  const material = new ShaderMaterial({ uniforms, vertexShader, fragmentShader })
  const geometry = new PlaneGeometry(2, 2)
  const mesh = new Mesh(geometry, material)
  scene.add(mesh)
  const startTime = performance.now() / 1000

  const setSize = () => {
    if (!active) return
    const w = container.clientWidth || 1, h = container.clientHeight || 1
    renderer.setSize(w, h, false)
    uniforms.iResolution.value.set(renderer.domElement.width, renderer.domElement.height, 1)
  }
  setSize()

  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => { if (active) setSize() }) : null
  if (ro) ro.observe(container)

  const targetMouse = new Vector2(-1000, -1000)
  const currentMouse = new Vector2(-1000, -1000)
  let targetInfluence = 0, currentInfluence = 0
  const targetParallax = new Vector2(0, 0), currentParallax = new Vector2(0, 0)

  const handlePointerMove = (e) => {
    const rect = renderer.domElement.getBoundingClientRect()
    const x = e.clientX - rect.left, y = e.clientY - rect.top
    const dpr = renderer.getPixelRatio()
    targetMouse.set(x * dpr, (rect.height - y) * dpr)
    targetInfluence = 1.0
    if (props.parallax) {
      targetParallax.set(((x - rect.width / 2) / rect.width) * props.parallaxStrength, -((y - rect.height / 2) / rect.height) * props.parallaxStrength)
    }
  }
  const handlePointerLeave = () => { targetInfluence = 0 }

  if (props.interactive) {
    renderer.domElement.addEventListener('pointermove', handlePointerMove)
    renderer.domElement.addEventListener('pointerleave', handlePointerLeave)
  }

  let raf = 0
  const loop = () => {
    if (!active) return
    uniforms.iTime.value = performance.now() / 1000 - startTime
    if (props.interactive) {
      currentMouse.lerp(targetMouse, props.mouseDamping); uniforms.iMouse.value.copy(currentMouse)
      currentInfluence += (targetInfluence - currentInfluence) * props.mouseDamping; uniforms.bendInfluence.value = currentInfluence
    }
    if (props.parallax) {
      currentParallax.lerp(targetParallax, props.mouseDamping); uniforms.parallaxOffset.value.copy(currentParallax)
    }
    renderer.render(scene, camera)
    raf = requestAnimationFrame(loop)
  }
  loop()

  cleanup = () => {
    active = false
    cancelAnimationFrame(raf)
    if (ro) ro.disconnect()
    if (props.interactive) {
      renderer.domElement.removeEventListener('pointermove', handlePointerMove)
      renderer.domElement.removeEventListener('pointerleave', handlePointerLeave)
    }
    geometry.dispose(); material.dispose(); renderer.dispose()
    renderer.forceContextLoss()
    if (renderer.domElement.parentElement) renderer.domElement.parentElement.removeChild(renderer.domElement)
  }
}

onMounted(() => setupScene())
onUnmounted(() => { if (cleanup) cleanup() })
</script>

<template>
  <div ref="containerRef" class="floating-lines-container" />
</template>

<style>
.floating-lines-container {
  width: 100%;
  height: 100%;
  min-height: 100vh;
  overflow: hidden;
}
</style>
