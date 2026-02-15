# 🏗️ AI-Powered DDR Generator

**[🔴 LIVE DEMO](https://ai-powered-ddr-generator-urbanroof.onrender.com/)** | **[📺 WATCH VIDEO DEMO](DEMO_SCRIPT.md)**

An intelligent web application that automates the creation of **Detailed Diagnostic Reports (DDR)** for building inspections. It takes raw inspection data (PDFs) and uses Large Language Models (LLM) to generate professional, structured reports.

![DDR Generator UI](frontend/public/vite.svg)

## 📌 a. What We Built
A full-stack web application combining a modern **React Frontend** with a robust **FastAPI Backend**.

- **Frontend**: A responsive, drag-and-drop interface built with React, TypeScript, and TailwindCSS.
- **Backend**: A Python FastAPI server that orchestrates the data processing pipeline.
- **AI Engine**: Integrated with **Groq (Llama 3.1 8B)** for ultra-fast text generation and analysis.
- **Pipeline**: A custom Python library (`ddr_generator`) that handles PDF extraction, data structuring, deduplication, and correlation analysis.

## ⚙️ b. How It Works
The system follows a multi-stage pipeline architecture:

1. **Upload**: User drags & drops an Inspection PDF into the web interface.
2. **Ingestion**: The backend receives the file and initializes the `DDRPipeline`.
3. **Extraction**: Text and structural data are extracted from the PDF using custom parsers.
4. **Processing**:
   - **Structuring**: Raw data is organized into logical areas.
   - **Deduplication**: Duplicate findings are removed (using rule-based logic).
   - **Correlation**: Issues are analyzed to find root causes.
   - **Severity**: An automated score (High/Medium/Low) is assigned.
5. **Generation**: The processed data is sent to the **Groq LLM** to write the narrative sections (Observations, Root Causes, Recommendations).
6. **Delivery**: The final Report (Markdown & JSON) is sent back to the frontend for display and download.

## 🚧 c. Limitations
While functional, the current MVP has accurate constraints:
1. **Synchronous Processing**: Large files may timeout if the analysis takes >60 seconds (browser/server limits).
2. **Ephemeral Storage**: Uploaded files and generated reports are stored temporarily on the server filesystem, which isn't suitable for scale (they are deleted/lost on restart).
3. **No Authentication**: The application is open; anyone with access can generate reports.
4. **Single-User Focus**: No user accounts or history tracking.
5. **PDF Layout Dependency**: The extraction relies on specific PDF structures; different report formats might fail.

## 🚀 d. How We Would Improve It (Future Roadmap)
To make this production-grade, we plan to:
1. **Async Job Queue**: Move processing to a background worker (Celery/Redis) to handle large files without timeouts.
2. **Cloud Storage**: Save reports to AWS S3 or Google Cloud Storage instead of local disk.
3. **Database Integration**: Use PostgreSQL to store user history, generated reports, and analytics.
4. **Authentication**: Add User Login (OAuth/Auth0) to secure the tool.
5. **Thermal Analysis**: Enable the "Thermal PDF" feature which is currently a placeholder.
6. **Custom Templates**: Allow users to customize the output report format/style.

---

## 🛠️ Local Setup

### Backend
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python ddr_generator/server.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
