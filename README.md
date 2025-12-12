# CodeMind AI 🧠

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![TypeScript](https://img.shields.io/badge/typescript-5.0%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14.0-black.svg?logo=next.js&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg?logo=tailwind-css&logoColor=white)

**CodeMind AI** is an intelligent code understanding and analysis platform designed to help developers navigate, understand, and interact with large codebases using natural language. Use the power of embeddings and semantic search to ask questions about your repository and get accurate, context-aware answers.

## 🚀 Features

-   **🔍 Semantic Code Search**: powered by ChromaDB and vector embeddings.
-   **💬 Chat with Code**: Context-aware Q&A using LLMs (LangChain).
-   **🌲 Accurate Parsing**: Uses Tree-sitter for robust code parsing across multiple languages.
-   **⚡ Real-time Analysis**: Fast and efficient backend powered by FastAPI.
-   **✨ Modern UI**: sleek, responsive interface built with Next.js and TailwindCSS.

## 🛠 Tech Stack

### Backend
-   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance Python web framework.
-   **Database**:
    -   **Vector Store**: [ChromaDB](https://www.trychroma.com/) for efficiently storing and retrieving high-dimensional embeddings.
    -   **Relational**: [PostgreSQL](https://www.postgresql.org/) (via [SQLAlchemy](https://www.sqlalchemy.org/)) for structured data.
-   **AI/ML**:
    -   **Orchestration**: [LangChain](https://python.langchain.com/) for building LLM applications.
    -   **Parsing**: [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) for concrete syntax tree generation.
-   **Utilities**: `pydantic` for data validation, `uvicorn` for ASGI server.

### Frontend
-   **Framework**: [Next.js 14](https://nextjs.org/) (App Router) for server-side rendering and static generation.
-   **Language**: [TypeScript](https://www.typescriptlang.org/) for type safety.
-   **Styling**: [TailwindCSS](https://tailwindcss.com/) for utility-first styling.
-   **Icons**: [Lucide React](https://lucide.dev/) for beautiful, consistent icons.
-   **HTTP Client**: `axios` for API requests.

## 📂 Project Structure

```
codemind-ai/
├── backend/                # Python FastAPI Backend
│   ├── app/
│   │   ├── config/         # Configuration settings
│   │   ├── routers/        # API Routes
│   │   ├── services/       # Business logic (parsing, embedding, GitHub)
│   │   └── main.py         # Application entry point
│   ├── tests/              # Pytest suites
│   └── requirements.txt    # Python dependencies
│
└── frontend/               # Next.js Frontend
    ├── app/                # App Router pages and layouts
    ├── components/         # Reusable React components
    ├── lib/                # Utility functions
    └── package.json        # Node.js dependencies
```

## 🏁 Getting Started

### Prerequisites

-   **Python 3.10+**
-   **Node.js 18+**
-   **PostgreSQL** (running locally or via Docker)

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and API keys

# Run migrations (if applicable)
# alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

The backend API will be available at `http://localhost:8000`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local

# Start the development server
npm run dev
```

The frontend application will be available at `http://localhost:3000`.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the repository
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
