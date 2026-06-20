# HatForge

An intelligent VST3 hi-hat generator plugin that analyzes incoming drum beats and creates context-aware hi-hat sequences using an autoregressive Transformer model. It maps natural language style prompts directly into musical logic, dynamically adapting to the user's beat. HatForge bridges a modern C++ JUCE interface with a real-time Python AI backend.

## Installation

### 1. Python Environment
Requires Python 3.11+
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. JUCE Plugin Build
Requires CMake 3.22+
```bash
cd phase3_juce_plugin
# Ensure JUCE is cloned or linked in vendor/JUCE
mkdir build && cd build
cmake ..
cmake --build .
```

## Usage

### Python-only Mode
Generate hats directly from a MIDI file using the rule-based prototype:
```bash
python phase1_prototype/generate_hats.py mybeat.mid --complexity 0.8
```

### With Prompt Engine
Generate using natural language descriptors:
```bash
python phase2_prompt_engine/prompt_parser.py "metro bounce"
```

### Full Plugin
1. Build the JUCE plugin and load it into FL Studio (or your DAW).
2. Start the AI server backend:
   ```bash
   python bridge/server.py
   ```
3. Send a beat into the plugin and generate hats!

## Architecture Diagram
```text
[ DAW (FL Studio) ] 
       │
[ HatForge VST3 ] <─── (MIDI via TCP) ───> [ bridge/server.py ]
       │                                          │
       ▼                                          ▼
[ Parameter UI ]                           [ Prompt Parser ]
                                                  │
                                                  ▼
                                           [ Transformer Model ]
                                           [ rule-based logic  ]
```

## Phase Completion Checklist
- [x] Phase 1: Python Prototype
- [x] Phase 2: Prompt Engine
- [x] Phase 3: JUCE VST3 Plugin Interface
- [x] Phase 4: AI Model & Inference Server
