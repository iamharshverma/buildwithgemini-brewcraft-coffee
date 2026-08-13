# BrewCraft — AI-Powered Personal Portfolio Concierge & Coffee Intelligence Agent

![BrewCraft Agent Demo](demo.gif)

**BrewCraft** is a sophisticated, conversational AI concierge that enables visitors to explore **Harsh Verma’s portfolio** — including technical blogs, research keynotes, awards, and services — while delivering precision brewing calculations, interactive UI templates, and lead capture.

---

## 🌟 Key Features

- **Personalized Portfolio Discovery**: Search and explore blogs, research papers, awards, and keynotes tailored to visitor interests.
- **Precision Specialty Coffee Guide**: Search single-origin coffee catalogs and calculate pour-over brew recipes (water target, bloom timing, and grind guides).
- **Service Consultations & Lead Capture**: Browse 1:1 strategy packages, enterprise cybersecurity audits, and book offerings, with automated lead capture.
- **Dynamic UI Template Switching**: Preview and switch UI themes (*Sleek Dark Mode Artisan*, *Glassmorphism Tech Hub*, *Neo-Brutalist Dashboard*) with user consent.
- **On-Demand Visual & Video Generation**: Synthesize portfolio images and short video clips using Google's latest multimodal models.
- **Secure Code Execution Sandbox**: Execute Python scripts for custom pricing logic, recommendation ranking, and data transformations.
- **A2UI Rich Card Rendering**: Render card-based UI surfaces directly in the chat interface using A2UI schema standards.

---

## ☁️ Google Cloud & Vertex AI Architecture

BrewCraft is built on Google Cloud's Agent Development Kit (ADK) and integrates with key Google Cloud services:

| GCP Tool / Service | Functionality |
| :--- | :--- |
| **Vertex AI Memory Bank** | Persists cross-session visitor intent signals, topic interests (AI, cybersecurity, agentic systems), and booking history. |
| **Google Cloud Firestore** | Stores portfolio records, visitor signals, and active UI preferences in a scalable NoSQL database. |
| **Cloud Storage** | Hosts public media assets and generated media in `gs://brewcraft-portfolio-media-qwiklabs-gcp-04-623529d65701`. |
| **RAG / RSS Feed Retrieval** | Ingests real-time tech blogs and research articles via RSS/Atom feeds for up-to-date knowledge retrieval. |
| **Gemini Image & Omni Video Generation** | Generates visuals via `gemini-3.1-flash-lite-image` and video clips via `gemini-omni-flash-preview` in the `global` region. |
| **A2UI (Agent-to-User Interface)** | Formats responses into structured card layouts via `A2uiSchemaManager` (v0.8) and `BasicCatalog`. |
| **Cloud Run & Agent Runtime** | Serves the FastAPI chat proxy and hosts the deployed ADK agent engine on Agent Platform. |

---

## 🚀 Quick Start

### 1. Local Development
```bash
# Install dependencies
uv sync

# Run interactive local playground
agents-cli playground
```

### 2. Run Local Frontend Proxy
```bash
cd frontend
pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/397519156454/locations/us-east1/reasoningEngines/1655864511430656000"
export AGENT_DIRECTORY="app"
python main.py
```
Open [http://localhost:8080](http://localhost:8080) to interact with the agent UI.

---

## 🧪 Testing & Evaluation

Run unit and integration tests:
```bash
uv run python -m pytest tests/unit tests/integration
```

Run agent quality evaluation:
```bash
agents-cli eval generate
agents-cli eval grade
```
