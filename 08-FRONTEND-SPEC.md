# Frontend Spec — React App

## Design identity

**Name:** Jnana Setu (ज्ञान सेतु)
**Palette:**
- Background: `#0F0E0B` (deep charcoal — like aged manuscript paper in dark)
- Surface: `#1A1916`
- Accent: `#C9923A` (saffron gold — Jain spiritual color)
- Text primary: `#F0EDE6`
- Text secondary: `#8C8880`
- Anuyoga colors:
  - Dravyanuyog: `#7C6AE8` (deep violet — philosophy)
  - Charananuyog: `#3B9E75` (sage green — ethics/nature)
  - Prathamanuyoga: `#C97A3A` (amber — history/stories)
  - Karnanuyoga: `#4A8FC9` (sky blue — cosmos)

**Typography:**
- Display: Crimson Pro (Google Fonts) — scholarly serif for headings
- Body: Inter — clean for chat text
- Mono: JetBrains Mono — code/citations

**Signature element:** A thin saffron-gold line (`#C9923A`) that animates across the top of the page on load — referencing the Jain symbol of infinite knowledge.

---

## Pages

### `/` — Home
```
┌─────────────────────────────────────┐
│  ज्ञान सेतु          [Login] [Sign up] │
├─────────────────────────────────────┤
│                                     │
│   "A bridge to 600 years of        │
│    Jain wisdom"                     │
│                                     │
│   [Daily Reflection Card]           │
│   Quote · Source · Contemplation    │
│                                     │
│   [Quick query input]               │
│   "Ask the library..."              │
│                                     │
│   [Explore the library →]           │
└─────────────────────────────────────┘
```

### `/chat` — Main chat
```
┌───────────────┬─────────────────────┐
│  Filters      │  Chat messages      │
│               │                     │
│  Author:      │  User: [message]    │
│  ○ All        │                     │
│  ● Vidyasagar │  AI: [streaming...] │
│  ○ Tarun Sagr │  [CitationCard]     │
│  ○ Gyanmati   │  [CitationCard]     │
│  ...          │                     │
│               │  [message input]    │
│  Anuyoga:     │  [Send]            │
│  ○ All        │                     │
│  ● Dravyanuyg │                     │
│  ○ Charananuy │                     │
└───────────────┴─────────────────────┘
```

### `/books` — Book explorer
```
┌─────────────────────────────────────┐
│  [Search books...]  [Filter ▼]      │
│  Anuyoga: [All][Dravya][Charana]... │
├─────────────────────────────────────┤
│  ┌────────┐ ┌────────┐ ┌────────┐  │
│  │Book    │ │Book    │ │Book    │  │
│  │card    │ │card    │ │card    │  │
│  └────────┘ └────────┘ └────────┘  │
│  ┌────────┐ ┌────────┐ ┌────────┐  │
│  │...     │ │...     │ │...     │  │
└─────────────────────────────────────┘
```

---

## Components

### `ChatWindow.tsx`
```typescript
// Props
interface ChatWindowProps {
  authorFilter: string[]
  anuyogaFilter: string
}

// State
- messages: Message[]
- isStreaming: boolean
- currentStreamText: string

// SSE hook usage
const { startStream } = useSSE({
  onToken: (token) => setCurrentStreamText(prev => prev + token),
  onCitations: (citations) => appendCitationsToLastMessage(citations),
  onDone: () => setIsStreaming(false)
})
```

### `CitationCard.tsx`
```typescript
interface Citation {
  book_id: string
  title: string
  title_hindi: string
  author: string
  anuyoga: string
  chapter: string
  excerpt: string
}

// Renders as a collapsible card below the AI message
// Shows: AnuyogaBadge + title + author + chapter
// Expands to show excerpt on click
```

### `AuthorFilter.tsx`
```typescript
const AUTHORS = [
  { slug: "all", label: "All sources" },
  { slug: "canonical", label: "Canonical texts" },
  { slug: "vidyasagar", label: "Acharya Vidyasagar Ji" },
  { slug: "vidyananda", label: "Acharya Vidyananda Ji" },
  { slug: "tarun_sagar", label: "Muni Tarun Sagar Ji" },
  { slug: "gyanmati", label: "Aryika Gyanmati Mataji" },
  { slug: "pushpadant_sagar", label: "Acharya Pushpadant Sagar Ji" },
  { slug: "deshbhushan", label: "Acharya Deshbhushan Ji" },
  { slug: "gupti_sagar", label: "Upadhyay Gupti Sagar Ji" },
  { slug: "vardhaman_sagar", label: "Acharya Vardhaman Sagar Ji" },
  { slug: "praman_sagar", label: "Muni Praman Sagar Ji" },
  { slug: "nirbhay_sagar", label: "Acharya Nirbhay Sagar Ji" },
  { slug: "pulak_sagar", label: "Pulak Sagar Ji" },
]
// Multi-select checkboxes
// "All" deselects others; selecting any author deselects "All"
```

### `AnuyogaBadge.tsx`
```typescript
const ANUYOGA_CONFIG = {
  dravyanuyog:   { label: "Philosophy", color: "#7C6AE8" },
  charananuyog:  { label: "Ethics",     color: "#3B9E75" },
  prathamanuyoga:{ label: "History",    color: "#C97A3A" },
  karnanuyoga:   { label: "Cosmology",  color: "#4A8FC9" },
}
// Renders as a small colored pill: ● Philosophy
```

### `useSSE.ts` hook
```typescript
export function useSSE() {
  const startStream = async (payload: QueryRequest) => {
    const response = await fetch('/query', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(payload)
    })
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const lines = decoder.decode(value).split('\n')
      for (const line of lines) {
        if (line.startsWith('event: token')) {
          // next line is data
        }
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))
          // dispatch based on event type
        }
      }
    }
  }
  return { startStream }
}
```

---

## State management (Zustand)

```typescript
// store/chatStore.ts
interface ChatStore {
  messages: Message[]
  authorFilter: string[]
  anuyogaFilter: string
  isStreaming: boolean
  user: User | null
  
  addMessage: (msg: Message) => void
  setAuthorFilter: (authors: string[]) => void
  setAnuyogaFilter: (anuyoga: string) => void
  setUser: (user: User | null) => void
  clearMessages: () => void
}
```

---

## Free vs Premium UI states

| Element | Free tier | Premium tier |
|---------|-----------|-------------|
| Daily reflection | ✓ Always | ✓ Always |
| Chat queries | 3/day, counter shown | Unlimited |
| Author filter | All options | All options |
| Anuyoga filter | All options | All options |
| Book explorer | Full access | Full access |
| Citation excerpts | First 100 chars | Full excerpt |
| Response language | English only | English + Hindi |
| Export chat | ✗ | ✓ |
