# Scribblr — AI-Powered Lecture Note Writer

A 3D-printed smart pen holder that listens to a professor, extracts key points using AI, and writes them on a chalkboard in real time.

**Audio → ElevenLabs STT → Gemini Summarization → G-code → Physical Writing**

## Inspiration
Many students struggle to keep up during lectures — whether it's unclear handwriting, complex explanations, zoning out, or missing content when arriving late. We wanted to solve the real frustration of losing information when professors erase the board too quickly or when note-taking becomes overwhelming. _Scribblr_ was inspired by blending traditional classroom tools with ambient AI to make learning more accessible and less stressful.

## What it does
**Scribblr** is a 3D-printed smart pen holder that acts as an automated lecture assistant. Using cameras, microphones, and sensors, it captures spoken explanations and whiteboard content, then transcribes and summarizes lectures in real time. Instead of replacing note-taking, Scribblr enhances it by generating structured summaries as the lecture happens.

## How we built it
We designed Scribblr as a compact hardware device combining vision, audio capture, and AI processing. The system listens to lectures, processes speech into text, and generates live summaries while monitoring the whiteboard visually. The workflow follows a pipeline of capturing → transcribing → summarizing → displaying, turning a simple desk object into an intelligent classroom companion.

## Challenges we ran into
One of the biggest challenges was balancing hardware constraints with real-time AI processing. Integrating microphones, cameras, and sensors into a small 3D-printed form factor required careful design decisions. Another challenge was ensuring summaries remained accurate while keeping latency low enough to feel **live** during a lecture environment.

## Accomplishments that we're proud of
We successfully transformed a familiar classroom object into an ambient AI assistant that strengthens traditional teaching instead of disrupting it. Seeing Scribblr transcribe and summarize lecture content live demonstrated the potential of combining robotics, AI, and education into one cohesive system.

## What we learned
Building Scribblr taught us how powerful agent-like AI systems can be when embedded into physical environments. We learned how to integrate hardware and software workflows, design for real-world classroom usability, and think about accessibility from a student's perspective.

## What's next for Scribblr
Next, we want to expand **personalized prompts** and adaptive summaries tailored to different learning styles. We also plan to improve contextual understanding of lectures and explore ways Scribblr could integrate into collaborative classroom environments.

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and paste your API keys:

```bash
cp .env.example .env
```

## Demo

### Software Demo (no hardware needed)

Full pipeline — mic → AI → live animated chalkboard on screen:

```bash
python3 demo.py --listen
```

Draw specific text:

```bash
python3 demo.py --text "HELLO WORLD"
```

Windowed mode (not fullscreen):

```bash
python3 demo.py --listen --windowed
```

### Hardware Demo (with 3D printer)

Same pipeline but also sends G-code to the machine via serial:

```bash
python3 demo.py --listen --serial
python3 demo.py --listen --serial --port /dev/cu.usbmodemSN234567892
```

### Controls

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `Escape` | Toggle fullscreen |
| Close window | Quit |

### Speed

Software demo runs at 15x speed by default. Override with `--speed`:

```bash
python3 demo.py --listen --speed 20
```

## Testing

```bash
# Test audio recording
python3 -m tests.test_audio

# Test ElevenLabs transcription
python3 -m tests.test_elevenlabs

# Test Gemini summarization
python3 -m tests.test_gemini

# Test G-code generation + preview image
python3 -m tests.test_gcode --text "HELLO WORLD" --save preview.png

# Test full pipeline (record → transcribe → summarize → preview)
python3 -m tests.test_pipeline --duration 10 --save preview.png

# Test serial communication
python3 -m tests.test_comm --mode serial
python3 -m tests.test_comm --mode dummy
```

## Project Structure

```
├── demo.py                  # Main demo entry point
├── python/
│   ├── config.py            # All tunable parameters
│   ├── audio_capture.py     # Background mic recording
│   ├── elevenlabs_stt.py    # Speech-to-text (ElevenLabs Scribe v2)
│   ├── gemini_api.py        # AI summarization (Gemini 2.5 Flash)
│   ├── text_to_gcode.py     # Text → G-code conversion (Hershey fonts)
│   ├── hershey_font.py      # Single-stroke vector font data
│   ├── machine_comm.py      # Serial/WiFi communication with printer
│   ├── live_display.py      # Real-time tkinter chalkboard display
│   └── main.py              # Headless pipeline (no display)
├── tests/                   # Individual component tests
├── .env.example             # API key template
└── requirements.txt         # Python dependencies
```

## Hardware

- Modified Lulzbot Taz 6 frame (~400x400mm)
- Ender 3 control board (Marlin firmware)
- X motor = horizontal movement
- Y + Z motors wired in parallel = vertical movement
- Chalk holder attached to print head
