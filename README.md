---
title: Exam Slayer V2
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Exam Slayer V2 🚀
### AI-Powered University Exam Preparation Engine

[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.2-646CFF.svg?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-Container-2496ED.svg?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Gemini API](https://img.shields.io/badge/Gemini_API-3.5_Flash-4285F4.svg?style=flat-square&logo=google-gemini&logoColor=white)](https://ai.google.dev/)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A5%97_Hugging_Face-Spaces-FFD21E.svg?style=flat-square)](https://huggingface.co/spaces)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

---

## 🎯 Why This Project Exists

University exam preparation is historically inefficient. Students waste valuable study hours manually sorting through dense, disorganized past question papers (PYQs), cross-referencing slides, searching scattered lecture transcripts, and typing out sample answers. 

**Exam Slayer V2** solves this bottleneck by automating the pipeline:
$$\text{Ingestion} \longrightarrow \text{Structure Parsing} \longrightarrow \text{AI Solving} \longrightarrow \text{Print-Ready Export}$$

By feeding raw course notes and question banks into a high-performance orchestration engine, students receive custom-tailored, exam-ready study packs and solved answer guides in seconds.

---

## 💻 Product Overview

Exam Slayer V2 operates in two distinct, production-tuned preparation modes:

*   **Study Guide Pack Mode (Notes-Only)**: Instantly processes unstructured course materials, textbooks, or presentation slides. The engine outputs conceptual summaries, intuitive analogies, memory tricks (mnemonics), predictive 2/5/10 mark exam questions, and lists of common academic pitfalls.
*   **Solved Answer Pack Mode (Notes + Questions)**: Takes a raw exam/question paper along with your study material. The engine parses individual questions, classifies their marks/cognitive levels, dynamically retrieves relevant source facts, synthesizes concise answers matching the mark constraints, and designs a comprehensive study key.

---

## ✨ Core Features

*   **Dual-Mode Compilation**: Pick between a structured revision guide (**Study Pack**) or a target-solved exam key (**Answer Pack**).
*   **Hybrid Question Parsing**: Combines deterministic structural rules (regex, typography) with Google Gemini AI normalization to isolate clean question boundaries from messy input documents.
*   **Marks-Aware Synthesis**: Adapts answer length and detail level based on question weights (e.g., short 2-mark definitions vs. comprehensive 10-mark architectural essays).
*   **Multi-Model Fallback Routing**: Leverages high-speed Gemini models with automatic routing and fallback logic to guarantee prompt delivery even during heavy API load.
*   **Advanced OCR Recovery**: Scanned exam papers, notes, or image-only documents are automatically processed through the `Tesseract OCR` pipeline to recover raw text.
*   **Beautiful PDF Rendering**: Uses `WeasyPrint` to compile a professional, paginated, print-ready PDF containing customized margins, elegant page breaks, covers, and typography styles.
*   **Dynamic Long-Form Batching**: Implements segmented prompts and windowed assembly to ensure large question banks can be answered in full without hitting output token caps.
*   **Docker Containerization & HF Spaces**: Built to run anywhere. Deployed seamlessly as a container on Hugging Face Spaces.

---

## 🏗️ Architecture Flow

Below is the conceptual flow of the Exam Slayer V2 compilation engine:

```text
    [ Question Bank / PYQ ]            [ Lecture Notes / Slides / PDFs ]
              │                                      │
              ▼                                      ▼
     Text Extraction & OCR                 Text Ingestion & Parsing
    (Tesseract / python-docx)             (Multi-file Document Parser)
              │                                      │
              ▼                                      ▼
    Deterministic Pre-Parser                 Knowledge Corpus
              │                                      │
              ▼                                      │
    Gemini Normalization &                           │
    Marks Classification                             │
              │                                      │
              ▼                                      │
        Routing Engine ◄─────────────────────────────┘
  (Dynamic Context Matching & RAG)
              │
              ▼
   Adaptive Answer Synthesis
  (Marks-Aware Context Windowing)
              │
              ▼
   HTML Layout Generation
  (Jinja2 & Tailwind Components)
              │
              ▼
    WeasyPrint PDF Engine
              │
              ▼
    [ Downloadable Exam Pack ]
```

---

## 🛠️ Tech Stack

### Frontend
*   **React** (TypeScript, SPA architecture)
*   **Vite** (Build tool & development server)
*   **Tailwind CSS** (Modern utility-first styling)
*   **Lucide React** (Crisp vector iconography)

### Backend
*   **Python 3.11**
*   **FastAPI** (High-performance API routing and async job processing)
*   **Uvicorn** (ASGI server)
*   **Jinja2** (Dynamic HTML compilation engine)

### AI & Language Models
*   **Google Gemini API** (Gemini 2.5 Flash & fallbacks for parsing, classification, and answering)
*   **Custom RAG & Context Window Manager**

### PDF & Document Processing
*   **WeasyPrint** (HTML-to-PDF compilation engine utilizing CSS Paged Media standards)
*   **Tesseract OCR** (Optical character recognition engine for scanned documents)
*   **python-docx, PyPDF2, python-pptx** (Native binary text extractors)

### Infrastructure
*   **Docker** (Multi-stage production build)
*   **Hugging Face Spaces** (Cloud hosting environment)

---

## 📸 Screenshots

| Upload Dashboard | Generation Progress |
| --- | --- |
| ![Upload Dashboard](https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80) | ![Processing Screen](https://images.unsplash.com/photo-1639762681485-074b7f938ba0?auto=format&fit=crop&w=600&q=80) |

| Solved Answer Pack Preview | PDF Print Output |
| --- | --- |
| ![Result Screen](https://images.unsplash.com/photo-1586075010923-2dd4570fb338?auto=format&fit=crop&w=600&q=80) | ![PDF Document Preview](https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80) |

*(Real application UI screenshot placeholders. Replaced with actual visuals upon final deployment.)*

---

## 🚀 Live Demo

Access the live, production-grade application running on Hugging Face Spaces:

🔗 **[https://manoj-v-exam-slayer-v2.hf.space](https://manoj-v-exam-slayer-v2.hf.space)**

---

## 💻 Local Installation & Setup

### Prerequisites
*   Python 3.11+
*   Node.js 18+
*   [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (Required for OCR of scanned images/PDFs)
*   [GTK+ / Pango / Cairo libraries](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) (Required by WeasyPrint for PDF rendering)

### 1. Setup Backend
Open a terminal in the `backend/` directory:

```powershell
# Move to backend folder
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Environment Variables
Create a file named `.env` in the `backend/` directory:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
TESSERACT_CMD=tesseract  # Adjust to absolute path if not in system PATH
DEBUG=True
FILE_RETENTION_HOURS=24
```

#### Run Backend Server
```powershell
uvicorn app.main:app --reload
```
The API documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 2. Setup Frontend
Open a terminal in the `frontend/` directory:

```powershell
# Move to frontend folder
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
The React frontend will launch on [http://localhost:5173](http://localhost:5173) and automatically proxy API calls to the local FastAPI backend.

---

## 🐳 Deployment

### Local Docker Build
Ensure Docker is installed, then run the following in the project root:

```bash
# Build the combined production image
docker build -t exam-slayer-v2 .

# Run the container locally
docker run -p 7860:7860 -e GEMINI_API_KEY="your_api_key" exam-slayer-v2
```
Access the application locally at [http://localhost:7860](http://localhost:7860).

### Hugging Face Space Deployment
The application is configured to deploy directly to Hugging Face Spaces using the Docker SDK:
1. Create a **Docker** Space on Hugging Face.
2. Add your `GEMINI_API_KEY` under the **Repository Secrets** in Space settings.
3. Add the Hugging Face Git remote and push the branch:
   ```bash
   git remote add hf https://huggingface.co/spaces/Manoj-V/Exam-Slayer-V2
   git push hf main
   ```

---

## 📖 Usage Guide

1.  **Select Preparation Mode**: Choose between **Study Guide Pack** or **Solved Answer Pack**.
2.  **Upload Lecture Materials**: Drag and drop notes, slides, or syllabus docs (up to 5 files, maximum 40MB total).
3.  **Upload Question Bank** *(Answer Pack Mode only)*: Select the past paper, question list, or assignment document.
4.  **Click Compile / Solve**: The backend processes document text, runs OCR if needed, extracts question blocks, queries Gemini with relevant context, and renders the result.
5.  **Download PDF**: Preview your answers directly in the web app, then download the beautifully paginated PDF for offline study.

---

## ⚠️ Known Limitations

*   **OCR Scanning Quality**: Scan quality directly affects text extraction. If a scanned document is heavily smudged, slanted, or blurry, WeasyPrint and Gemini may receive incomplete text.
*   **Context Grounding**: AI answers are grounded in the uploaded study materials. If your uploaded notes do not contain the concepts required to answer a specific question, the engine will attempt to answer using general academic reasoning, but specificity may decrease.
*   **Mathematical Formula Formatting**: Extremely complex, multi-line mathematical matrices or hand-drawn schematics in scanned papers may not translate perfectly through plain text OCR.

---

## 🗺️ Future Roadmap

*   **Smarter Subject-Aware Agents**: Integration of specialized solvers for mathematical equations (e.g. SymPy integration) and programming questions (syntax-highlit code blocks).
*   **Adaptive Styling Templates**: Choice of multiple professional CSS templates for the generated PDF packs (e.g. Executive, Academic, Minimalist, Dark Theme).
*   **Semantic Pack Caching**: Implement vector-based caching of similar questions to cut API latency and decrease generation costs.
*   **Real-time Collaborative Sharing**: Sharing links for solved study packs, allowing class peers to study from the same compiled pack.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
