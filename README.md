# Code Space Techlab — AI Quality Control & Complaint Management System

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Streamlit 1.35+](https://img.shields.io/badge/streamlit-1.35+-red.svg)](https://streamlit.io/)
[![ChromaDB Vector Store](https://img.shields.io/badge/chromadb-hybrid--rag-purple.svg)](https://www.trychroma.com/)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-darkgreen.svg)](#)

An enterprise, production-minded AI quality assurance and complaint investigation platform built for **Code Space Techlab**, a manufacturer supplying precision products to **IKEA**, global retailers, and direct contract customers.

---

## 📌 Primary Business Objectives

1. **Product-Wise Knowledge Management:** Store and retrieve approved engineering specifications, BOM declarations, chemical safety documentation (REACH SVHC, EN 717-1), and customer-specific standards (e.g. IKEA flat-pack packaging).
2. **End-to-End Complaint Lifecycle:** Accept and investigate customer and internal complaints (`Submitted` ➔ `Triaged` ➔ `Under Investigation` ➔ `Awaiting Evidence/Testing` ➔ `Manager Review` ➔ `Approved`/`Rejected`/`Escalated` ➔ `Closed`).
3. **Deterministic Quality Evaluation Engine:** Evaluate complaints against approved product criteria using configurable numeric tolerances, boolean checks, required document audits, and weighted scoring with **mandatory failure overrides**.
4. **Compliance & Gap Analysis:** Detect missing required document categories, expired revisions, and chemical safety gaps.
5. **4-Tier Risk Matrix & Escalation:** Objectively compute risk based on Severity, Recurrence Frequency, and Affected Units. Automatic escalation triggers for product safety hazards.
6. **Root-Cause Analysis & CAPA:** AI-assisted engineering hypotheses across 8 disciplines with containment, corrective, and preventive action tracking.
7. **Traceability & Grounded Citations:** Link every AI finding to exact source document IDs, revisions, page numbers, and section headings.
8. **Role-Based Access Control & Audit:** Role isolation for Administrators, Quality Managers, Quality Engineers, Management Viewers, and external Customers.

---

## 🏛️ System Architecture

```
Quality_check_RAG/
├── app.py                         # Streamlit entrypoint & role authentication portal
├── pages/
│   ├── 01_Dashboard.py          # Real-time KPIs, Plotly trend charts, risk funnels
│   ├── 02_Products.py           # Product catalog & IKEA customer-specific specs
│   ├── 03_Documents.py          # Multi-format ingestion, chunk explorer, RAG assistant
│   ├── 04_Complaints.py         # Intake form, bulk CSV import, case lifecycle audit
│   ├── 05_Quality_Evaluation.py # Deterministic rules, explainable scoring, manager sign-off
│   ├── 06_Compliance.py         # Document gap auditor, 4-tier risk matrix, CAPA tracker
│   ├── 07_Reports.py            # PDF investigation reports, multi-tab Excel, and CSVs
│   └── 08_Admin_Settings.py     # User RBAC, criteria builder, system audit logs
├── src/
│   ├── config.py                  # Pydantic Settings configuration & paths
│   ├── database/                  # SQLite connection pool (WAL mode) and DDL schema
│   ├── auth/                      # PBKDF2-SHA256 password hashing & RBAC permissions
│   ├── products/                  # Product and customer-specific standards service
│   ├── document_processing/       # PDF, DOCX, XLSX, CSV parsers and structure-aware chunker
│   ├── retrieval/                 # ChromaDB semantic search + SQLite FTS5 BM25 hybrid retriever
│   ├── rag/                       # Injection-hardened prompt builder, LLM adapter, citations
│   ├── quality_engine/            # Criteria manager, deterministic rule evaluator, scorer
│   ├── complaint_management/      # Complaint lifecycle service and CAPA workflow
│   ├── compliance/                # Document gap analyzer and 4-tier risk matrix
│   ├── reporting/                 # ReportLab PDF compiler and openpyxl Excel exporter
│   ├── audit/                     # Immutable audit logger
│   └── api/                       # Headless FastAPI router and Pydantic schemas
├── scripts/
│   └── seed_demo_data.py          # Synthetic demo seeder initializing all 8 workflows
├── tests/                         # Pytest test suite (18 automated tests)
├── data/                          # Uploads, processed text, and ChromaDB vector store
├── requirements.txt               # Pinned dependencies
├── pytest.ini                     # Pytest configuration
├── Dockerfile                     # Production container definition
└── .env.example                   # Environment configuration template
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone <repository_url>
cd Quality_check_RAG

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Demo Dataset
The platform includes an optional, clearly labeled synthetic demo dataset featuring fictional products, specifications, and realistic complaints:
```bash
python scripts/seed_demo_data.py
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## 🔐 Demo User Accounts & Roles

All demo accounts share the default password: **`Quality2026!`**

| Username | Role | Scope / Permissions |
| :--- | :--- | :--- |
| `admin` | **Admin** | Full system administration, criteria builder, user management, audit logs |
| `manager1` | **Quality Manager** | Evaluation approvals, manager sign-offs, complaint closure, CAPA sign-off |
| `engineer1` | **Quality Engineer** | Investigation execution, rule evaluations, document uploads, CAPA updates |
| `ikea_rep` | **Customer (IKEA)** | Customer-isolated access: can only view and submit IKEA-related complaints |
| `viewer1` | **Management Viewer** | Read-only executive dashboard and downloadable reports |

> **Tip:** The login screen provides 1-click **Quick Demo Role Selection** buttons to instantly test role-based access control and customer data isolation.

---

## 🧪 Running Automated Tests

The codebase includes an automated test suite verifying critical business logic:
- Authentication & password hashing
- Role-based permissions and customer data isolation
- Structure-aware document chunking and text normalization
- Deterministic quality evaluation rules and **mandatory failure overrides**
- Hybrid RAG retrieval (ChromaDB + SQLite FTS5 BM25)
- Prompt injection protection and citation grounding
- Complaint lifecycle status transitions and audit history
- ReportLab PDF and openpyxl Excel generation
- Headless FastAPI REST endpoints

Run all tests via Pytest:
```bash
pytest -v
```

---

## 🌐 Headless REST API (Future Website Integration)

The business logic is decoupled from Streamlit widgets and exposed via FastAPI in `src/api/router.py`:

```bash
# Run FastAPI server
uvicorn src.api.router:api_app --reload --port 8000
```

Interactive API documentation will be available at `http://localhost:8000/docs`:
- `GET  /api/v1/health` — Readiness probe
- `GET  /api/v1/products` — Catalog lookup
- `POST /api/v1/complaints` — Submit complaint
- `GET  /api/v1/complaints/{id}` — Case details and timeline
- `POST /api/v1/complaints/{id}/evaluate` — Trigger quality rule evaluation
- `POST /api/v1/knowledge/query` — Grounded RAG inquiry with citations
- `POST /api/v1/evaluations/{id}/approve` — Quality Manager sign-off

---

## 🛡️ Security & Production Deployment Considerations

1. **Confidentiality:** Documents and customer communications are isolated. Customer users can never view other customers' specifications or confidential internal notes.
2. **Prompt-Injection Defense:** All uploaded documents and complaint narratives are fenced in `<untrusted_document_context>` tags with strict directives preventing LLM behavior override.
3. **Database Migration:** For multi-server production deployment, replace SQLite with PostgreSQL by modifying `DB_PATH` in `.env` to a SQLAlchemy/Postgres connection string.
4. **Local vs Hosted LLM:** By default, the system operates completely offline using Sentence Transformers embeddings and a deterministic rule engine. To connect a local LLM, run Ollama with `llama3` (`http://localhost:11434`), or supply an `OPENAI_API_KEY` in `.env`.
