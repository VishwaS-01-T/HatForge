# Data Collection

- **Groove MIDI Dataset (Google Magenta)** — 13.6 hours of drum MIDI
  - URL: https://magenta.tensorflow.org/datasets/groove
  - Contains: kick, snare, hat patterns from real drummers
  - Use: primary training data
  
- **MIDI Trap Dataset**
  - Search HuggingFace for "trap midi dataset"
  - Filter: BPM 130–160, genre tag = trap
  
- **Custom Scrape Fallback**
  - If datasets unavailable, use synthetic MIDI patterns generated using the Phase 1 rule-based generator (clearly labeled as synthetic).
