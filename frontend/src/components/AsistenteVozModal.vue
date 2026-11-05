<template>
  <div v-if="visible" class="asistente">
    <section
      v-if="abierto"
      class="asistente-panel"
      role="dialog"
      aria-label="Asistente SIA"
      @keydown.esc="cerrar"
    >
      <header class="asistente-cabecera">
        <div>
          <h2>Asistente SIA</h2>
          <p>Soporte técnico · EMI Santa Cruz</p>
        </div>
        <div class="asistente-cabecera-acciones">
          <button
            type="button"
            class="asistente-icono"
            :class="{ activo: vozActiva }"
            :disabled="!soportaSintesis"
            :title="soportaSintesis ? (vozActiva ? 'Silenciar respuestas' : 'Leer respuestas en voz alta') : 'Este navegador no puede leer en voz alta'"
            :aria-pressed="vozActiva"
            @click="alternarVoz"
          >
            <svg v-if="vozActiva" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4zm12.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z"/></svg>
            <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4zm12.6 3 2.7-2.7-1.4-1.4-2.7 2.7-2.7-2.7-1.4 1.4 2.7 2.7-2.7 2.7 1.4 1.4 2.7-2.7 2.7 2.7 1.4-1.4z"/></svg>
          </button>
          <button type="button" class="asistente-icono" title="Cerrar" aria-label="Cerrar asistente" @click="cerrar">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.3 5.7 12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7l-1.4-1.4L9.2 12 2.9 5.7l1.4-1.4 6.3 6.3 6.3-6.3z"/></svg>
          </button>
        </div>
      </header>

      <div ref="lista" class="asistente-mensajes" aria-live="polite">
        <article
          v-for="(m, i) in mensajes"
          :key="i"
          class="asistente-mensaje"
          :class="m.rol"
        >
          <p>{{ m.contenido }}</p>
          <button
            v-if="m.rol === 'asistente' && soportaSintesis"
            type="button"
            class="asistente-escuchar"
            @click="hablar(m.contenido)"
          >
            Escuchar
          </button>
        </article>
        <p v-if="enviando" class="asistente-escribiendo">El asistente está escribiendo…</p>
      </div>

      <p v-if="aviso" class="asistente-aviso">{{ aviso }}</p>

      <form class="asistente-entrada" @submit.prevent="enviar">
        <button
          type="button"
          class="asistente-microfono"
          :class="{ escuchando }"
          :disabled="!soportaReconocimiento || enviando"
          :title="soportaReconocimiento ? (escuchando ? 'Detener dictado' : 'Dictar pregunta') : 'Este navegador no permite dictar. Use Chrome o Edge.'"
          :aria-pressed="escuchando"
          @click="alternarDictado"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21h2v-3.1a7 7 0 0 0 6-6.9h-2z"/></svg>
        </button>
        <textarea
          ref="campo"
          v-model="texto"
          rows="2"
          maxlength="1000"
          :placeholder="escuchando ? 'Escuchando…' : 'Escriba o dicte su pregunta'"
          :disabled="enviando"
          @keydown.enter.exact.prevent="enviar"
        ></textarea>
        <button type="submit" class="asistente-enviar" :disabled="enviando || !texto.trim()" aria-label="Enviar pregunta">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 20.5 21 12 3 3.5v6.6l12 1.9-12 1.9z"/></svg>
        </button>
      </form>
    </section>

    <button
      type="button"
      class="asistente-boton"
      :aria-expanded="abierto"
      aria-label="Abrir Asistente SIA"
      @click="abierto ? cerrar() : abrir()"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a2 2 0 0 1 1 3.7V7h5a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-8a3 3 0 0 1 3-3h5V5.7A2 2 0 0 1 12 2zM8.5 12a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm7 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM1 12h1v4H1zm21 0h1v4h-1z"/></svg>
      <span>Asistente</span>
    </button>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const BIENVENIDA = 'Hola, soy el Asistente SIA. Puedo orientarle sobre Soporte Técnico, Mantenimiento, Compras Caja Chica y el estado de sus trámites. Escriba su pregunta o presione el micrófono para dictarla.'
const CLAVE_VOZ = 'sigta_asistente_voz'
const MAXIMO_HISTORIAL = 6

const route = useRoute()
const token = ref(localStorage.getItem('sigta_token'))
const visible = computed(() => !!token.value && route.meta.requiereAuth && route.path !== '/cambiar-contrasena')

const abierto = ref(false)
const mensajes = ref([{ rol: 'asistente', contenido: BIENVENIDA, inicial: true }])
const texto = ref('')
const enviando = ref(false)
const aviso = ref('')
const lista = ref(null)
const campo = ref(null)

const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition
const soportaReconocimiento = !!Reconocimiento
const soportaSintesis = 'speechSynthesis' in window
const escuchando = ref(false)
const vozActiva = ref(soportaSintesis && localStorage.getItem(CLAVE_VOZ) !== 'no')
let reconocimiento = null
let vozEspanol = null

watch(() => route.fullPath, () => {
  token.value = localStorage.getItem('sigta_token')
  if (!visible.value) cerrar()
})

watch(() => mensajes.value.length, async () => {
  await nextTick()
  if (lista.value) lista.value.scrollTop = lista.value.scrollHeight
})

function abrir() {
  abierto.value = true
  nextTick(() => campo.value?.focus())
}

function cerrar() {
  abierto.value = false
  detenerDictado()
  detenerVoz()
}

// ==========================================================
// CONSULTA AL BACKEND
// ==========================================================

function historial() {
  return mensajes.value
    .filter(m => !m.inicial && !m.error)
    .slice(-MAXIMO_HISTORIAL)
    .map(m => ({ rol: m.rol, contenido: m.contenido }))
}

function mensajeDeError(respuesta, datos) {
  if (respuesta.status === 401) return 'Su sesión expiró. Inicie sesión nuevamente para seguir usando el asistente.'
  if (respuesta.status === 429) return 'Hizo muchas consultas seguidas. Espere un momento e intente de nuevo.'
  return datos.detalle || 'El asistente no pudo responder en este momento.'
}

async function enviar() {
  const pregunta = texto.value.trim()
  if (!pregunta || enviando.value) return

  detenerDictado()
  const previo = historial()
  mensajes.value.push({ rol: 'usuario', contenido: pregunta })
  texto.value = ''
  aviso.value = ''
  enviando.value = true

  try {
    const respuesta = await fetch('/api/asistente/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Token ${localStorage.getItem('sigta_token')}`,
      },
      body: JSON.stringify({ mensaje: pregunta, historial: previo }),
    })
    const datos = await respuesta.json().catch(() => ({}))

    if (!respuesta.ok || !datos.ok) {
      mensajes.value.push({ rol: 'asistente', contenido: mensajeDeError(respuesta, datos), error: true })
      return
    }

    mensajes.value.push({ rol: 'asistente', contenido: datos.respuesta })
    if (vozActiva.value) hablar(datos.respuesta)
  } catch {
    mensajes.value.push({ rol: 'asistente', contenido: 'No fue posible comunicarse con el servidor. Revise su conexión e intente nuevamente.', error: true })
  } finally {
    enviando.value = false
    nextTick(() => campo.value?.focus())
  }
}

// ==========================================================
// VOZ A TEXTO (Web Speech API)
// ==========================================================

const ERRORES_DICTADO = {
  'not-allowed': 'El navegador bloqueó el micrófono. Permita el acceso al micrófono para este sitio.',
  'service-not-allowed': 'El navegador bloqueó el micrófono. Permita el acceso al micrófono para este sitio.',
  'no-speech': 'No se detectó voz. Presione el micrófono y hable cerca del equipo.',
  'audio-capture': 'No se encontró un micrófono conectado.',
  network: 'El dictado necesita conexión a internet en este navegador.',
}

function alternarDictado() {
  escuchando.value ? detenerDictado() : iniciarDictado()
}

function iniciarDictado() {
  if (!soportaReconocimiento) return
  detenerVoz()
  aviso.value = ''

  const textoPrevio = texto.value.trim()
  reconocimiento = new Reconocimiento()
  reconocimiento.lang = 'es-BO'
  reconocimiento.interimResults = true
  reconocimiento.continuous = false

  reconocimiento.onresult = evento => {
    const dictado = Array.from(evento.results).map(r => r[0].transcript).join('')
    texto.value = `${textoPrevio} ${dictado}`.trim()
  }
  reconocimiento.onerror = evento => {
    if (evento.error !== 'aborted') aviso.value = ERRORES_DICTADO[evento.error] || 'No se pudo reconocer la voz. Intente nuevamente.'
  }
  reconocimiento.onend = () => {
    escuchando.value = false
    reconocimiento = null
    campo.value?.focus()
  }

  reconocimiento.start()
  escuchando.value = true
}

function detenerDictado() {
  reconocimiento?.stop()
}

// ==========================================================
// TEXTO A VOZ (speechSynthesis)
// ==========================================================

function elegirVoz() {
  const voces = window.speechSynthesis.getVoices()
  vozEspanol =
    voces.find(v => v.lang === 'es-BO') ||
    voces.find(v => /^es-(419|MX|US|AR|CO|PE|CL)/.test(v.lang)) ||
    voces.find(v => v.lang.startsWith('es')) ||
    null
}

function alternarVoz() {
  vozActiva.value = !vozActiva.value
  localStorage.setItem(CLAVE_VOZ, vozActiva.value ? 'si' : 'no')
  if (!vozActiva.value) detenerVoz()
}

function hablar(contenido) {
  if (!soportaSintesis) return
  detenerVoz()

  // Chrome corta las locuciones largas; se leen frase por frase.
  const frases = contenido
    .replace(/[*_#`]/g, '')
    .match(/[^.!?\n]+[.!?]*/g) || []

  for (const frase of frases.map(f => f.trim()).filter(Boolean)) {
    const locucion = new SpeechSynthesisUtterance(frase)
    locucion.lang = vozEspanol?.lang || 'es-ES'
    if (vozEspanol) locucion.voice = vozEspanol
    window.speechSynthesis.speak(locucion)
  }
}

function detenerVoz() {
  if (soportaSintesis) window.speechSynthesis.cancel()
}

onMounted(() => {
  if (!soportaSintesis) return
  elegirVoz()
  window.speechSynthesis.addEventListener('voiceschanged', elegirVoz)
})

onUnmounted(() => {
  cerrar()
  if (soportaSintesis) window.speechSynthesis.removeEventListener('voiceschanged', elegirVoz)
})
</script>

<style scoped>
.asistente {
  font-family: var(--sigta-fuente);
}

.asistente-boton {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px 12px 14px;
  border: 2px solid var(--sigta-mostaza);
  border-radius: 999px;
  background: var(--sigta-azul);
  color: var(--sigta-blanco);
  font: 600 14px var(--sigta-fuente);
  box-shadow: var(--sigta-sombra-fuerte);
  cursor: pointer;
}

.asistente-boton:hover {
  background: var(--sigta-azul-medio);
}

.asistente-boton svg {
  width: 22px;
  height: 22px;
  fill: var(--sigta-mostaza);
}

.asistente-panel {
  position: fixed;
  right: 24px;
  bottom: 88px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  width: 380px;
  height: min(580px, calc(100vh - 120px));
  overflow: hidden;
  border: 1px solid var(--sigta-borde);
  border-radius: 14px;
  background: var(--sigta-superficie);
  box-shadow: var(--sigta-sombra-fuerte);
}

.asistente-cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 3px solid var(--sigta-mostaza);
  background: var(--sigta-azul);
  color: var(--sigta-blanco);
}

.asistente-cabecera h2 {
  margin: 0;
  font-size: 16px;
}

.asistente-cabecera p {
  margin: 2px 0 0;
  font-size: var(--sigta-chico);
  color: var(--sigta-azul-texto-claro);
}

.asistente-cabecera-acciones {
  display: flex;
  gap: 6px;
}

.asistente-icono {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: rgba(255, 255, 255, .12);
  cursor: pointer;
}

.asistente-icono svg {
  width: 18px;
  height: 18px;
  fill: var(--sigta-blanco);
}

.asistente-icono.activo svg {
  fill: var(--sigta-mostaza);
}

.asistente-icono:disabled {
  opacity: .4;
  cursor: not-allowed;
}

.asistente-mensajes {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  overflow-y: auto;
  background: var(--sigta-fondo);
}

.asistente-mensaje {
  max-width: 85%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: var(--sigta-texto-tam);
  line-height: 1.5;
}

.asistente-mensaje p {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.asistente-mensaje.asistente {
  align-self: flex-start;
  border: 1px solid var(--sigta-borde);
  border-bottom-left-radius: 4px;
  background: var(--sigta-superficie);
  color: var(--sigta-texto);
}

.asistente-mensaje.usuario {
  align-self: flex-end;
  border-bottom-right-radius: 4px;
  background: var(--sigta-azul);
  color: var(--sigta-blanco);
}

.asistente-escuchar {
  margin-top: 6px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--sigta-azul-medio);
  font: 600 var(--sigta-chico) var(--sigta-fuente);
  cursor: pointer;
}

.asistente-escribiendo {
  margin: 0;
  font-size: var(--sigta-chico);
  color: var(--sigta-texto-suave);
  font-style: italic;
}

.asistente-aviso {
  margin: 0;
  padding: 8px 14px;
  background: var(--sigta-alerta-fondo);
  color: var(--sigta-alerta);
  font-size: var(--sigta-chico);
}

.asistente-entrada {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px;
  border-top: 1px solid var(--sigta-borde);
  background: var(--sigta-superficie);
}

.asistente-entrada textarea {
  flex: 1;
  min-height: 40px;
  max-height: 120px;
  padding: 9px 10px;
  border: 1px solid var(--sigta-borde);
  border-radius: 10px;
  color: var(--sigta-texto);
  font: var(--sigta-texto-tam) / 1.4 var(--sigta-fuente);
  resize: none;
}

.asistente-entrada textarea:focus {
  outline: 2px solid var(--sigta-azul-claro);
  border-color: var(--sigta-azul-medio);
}

.asistente-microfono,
.asistente-enviar {
  display: grid;
  place-items: center;
  flex: none;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 0;
  border-radius: 10px;
  cursor: pointer;
}

.asistente-microfono {
  background: var(--sigta-azul-tenue);
}

.asistente-microfono svg {
  width: 20px;
  height: 20px;
  fill: var(--sigta-azul);
}

.asistente-microfono.escuchando {
  background: var(--sigta-error);
  animation: pulso 1.2s ease-in-out infinite;
}

.asistente-microfono.escuchando svg {
  fill: var(--sigta-blanco);
}

.asistente-enviar {
  background: var(--sigta-azul);
}

.asistente-enviar svg {
  width: 18px;
  height: 18px;
  fill: var(--sigta-blanco);
}

.asistente-microfono:disabled,
.asistente-enviar:disabled {
  opacity: .45;
  cursor: not-allowed;
}

@keyframes pulso {
  50% { box-shadow: 0 0 0 6px rgba(180, 35, 24, .2); }
}

@media (max-width: 560px) {
  .asistente-boton {
    right: 14px;
    bottom: 14px;
  }

  .asistente-boton span {
    display: none;
  }

  .asistente-panel {
    right: 10px;
    left: 10px;
    bottom: 78px;
    width: auto;
    height: calc(100vh - 100px);
  }
}
</style>
