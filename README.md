---
title: Exam Slayer V2
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Exam Slayer V2

FastAPI backend for turning uploaded study materials into exam-ready study pack PDFs using OCR, Gemini, and WeasyPrint.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Required environment variables live in `backend/.env` and are intentionally not committed:

- `GEMINI_API_KEY`
- `TESSERACT_CMD`

Health check:

```text
GET /api/v1/health
```
