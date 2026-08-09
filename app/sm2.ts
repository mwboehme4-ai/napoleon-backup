// Napoleon - SM-2 Lernlogik + IndexedDB-Persistenz

const DB_NAME = 'napoleon'
const DB_VERSION = 1
const STORE_CARDS = 'cards'
const STORE_META = 'meta'

export const NEUE_PRO_TAG = 30

export interface Card {
  id: string
  ease: number
  interval: number
  reps: number
  lapses: number
  due: string          // YYYY-MM-DD
  lastReview: string | null
  state: 'new' | 'learning' | 'review'
}

export type Bewertung = 'nochmal' | 'schwer' | 'gut' | 'einfach'

function heute(): string {
  return new Date().toISOString().slice(0, 10)
}

function plusTage(tage: number): string {
  const d = new Date()
  d.setDate(d.getDate() + Math.round(tage))
  return d.toISOString().slice(0, 10)
}

export function neueKarte(id: string): Card {
  return {
    id,
    ease: 2.5,
    interval: 0,
    reps: 0,
    lapses: 0,
    due: heute(),
    lastReview: null,
    state: 'new',
  }
}

// --- SM-2 (Anki-Variante mit vier Knoepfen) ---
export function bewerte(karte: Card, b: Bewertung): Card {
  const k: Card = { ...karte }
  k.lastReview = heute()

  if (b === 'nochmal') {
    k.reps = 0
    k.lapses += 1
    k.ease = Math.max(1.3, k.ease - 0.2)
    k.interval = 0
    // Zeitstempel statt Datum: Karte kommt in ~10 Minuten wieder,
    // nicht sofort nach dem naechsten Reload.
    k.due = new Date(Date.now() + 10 * 60 * 1000).toISOString()
    k.state = 'learning'
    return k
  }

  if (b === 'schwer') {
    k.ease = Math.max(1.3, k.ease - 0.15)
    k.interval = k.interval < 1 ? 1 : k.interval * 1.2
  } else if (b === 'gut') {
    if (k.reps === 0) k.interval = 1
    else if (k.reps === 1) k.interval = 6
    else k.interval = k.interval * k.ease
  } else { // einfach
    k.ease = Math.min(2.7, k.ease + 0.15)
    if (k.reps === 0) k.interval = 2
    else if (k.reps === 1) k.interval = 8
    else k.interval = k.interval * k.ease * 1.3
  }

  k.reps += 1
  k.interval = Math.max(1, Math.min(k.interval, 365))
  k.due = plusTage(k.interval)
  k.state = 'review'
  return k
}

// --- IndexedDB ---
function oeffne(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE_CARDS)) {
        db.createObjectStore(STORE_CARDS, { keyPath: 'id' })
      }
      if (!db.objectStoreNames.contains(STORE_META)) {
        db.createObjectStore(STORE_META, { keyPath: 'key' })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

function alleKarten(db: IDBDatabase): Promise<Card[]> {
  return new Promise((resolve, reject) => {
    const req = db.transaction(STORE_CARDS, 'readonly')
                  .objectStore(STORE_CARDS).getAll()
    req.onsuccess = () => resolve(req.result as Card[])
    req.onerror = () => reject(req.error)
  })
}

export async function speichereKarte(karte: Card): Promise<void> {
  const db = await oeffne()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_CARDS, 'readwrite')
    tx.objectStore(STORE_CARDS).put(karte)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

/**
 * Legt fuer alle uebergebenen IDs Karten an, die noch keine haben.
 * Bestehende Karten werden NIE ueberschrieben - das schuetzt den
 * Lernfortschritt bei jedem Reload und nach jedem Merge neuer Woerter.
 */
export async function migriere(ids: string[]): Promise<{neu: number, gesamt: number}> {
  const db = await oeffne()
  const vorhanden = await alleKarten(db)
  const bekannt = new Set(vorhanden.map(k => k.id))
  const fehlend = ids.filter(id => !bekannt.has(id))

  if (fehlend.length) {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction([STORE_CARDS, STORE_META], 'readwrite')
      const store = tx.objectStore(STORE_CARDS)
      fehlend.forEach(id => store.add(neueKarte(id)))
      tx.objectStore(STORE_META).put({ key: 'migratedAt', value: new Date().toISOString() })
      tx.objectStore(STORE_META).put({ key: 'wordCount', value: ids.length })
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  }
  return { neu: fehlend.length, gesamt: vorhanden.length + fehlend.length }
}

/** Faellige Karten fuer heute: alle Wiederholungen + max. NEUE_PRO_TAG neue. */
export async function faelligeKarten(limitNeu = NEUE_PRO_TAG): Promise<Card[]> {
  const db = await oeffne()
  const alle = await alleKarten(db)
  const h = heute()

  const jetzt = new Date().toISOString()
  const wiederholung = alle.filter(k => {
    if (k.state === 'new') return false
    // Lernphase nutzt volle Zeitstempel, Wiederholungen nur das Datum
    return k.due.length > 10 ? k.due <= jetzt : k.due <= h
  })
  const neue = alle.filter(k => k.state === 'new').slice(0, limitNeu)

  const zusammen = [...wiederholung, ...neue]
  // mischen
  for (let i = zusammen.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[zusammen[i], zusammen[j]] = [zusammen[j], zusammen[i]]
  }
  return zusammen
}

export async function statistik() {
  const db = await oeffne()
  const alle = await alleKarten(db)
  const h = heute()
  return {
    gesamt: alle.length,
    neu: alle.filter(k => k.state === 'new').length,
    faellig: alle.filter(k => k.state !== 'new' && k.due <= h).length,
    gelernt: alle.filter(k => k.reps > 0).length,
  }
}

/** Nur fuer Notfaelle - loescht den gesamten Lernfortschritt. */
export async function zuruecksetzen(): Promise<void> {
  const db = await oeffne()
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORE_CARDS, STORE_META], 'readwrite')
    tx.objectStore(STORE_CARDS).clear()
    tx.objectStore(STORE_META).clear()
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}
