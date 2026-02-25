# AI Legal Assistant 🤖⚖️

> An intelligent legal document analysis and Q&A system powered by RAG (Retrieval-Augmented Generation) technology

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.1.1-61DAFB.svg?style=flat&logo=react)](https://reactjs.org/)
[![LangChain](https://img.shields.io/badge/LangChain-0.2.11-FF6B35.svg?style=flat)](https://langchain.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-1.55.3-412991.svg?style=flat&logo=openai)](https://openai.com/)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Monitoring & Analytics](#monitoring--analytics)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

The AI Legal Assistant is a comprehensive solution that combines advanced natural language processing with legal document analysis capabilities. It leverages hybrid retrieval methods (semantic + keyword search) to provide accurate, contextual answers to legal questions while maintaining transparency through source attribution.

### Demo

![AI Legal Assistant Demo](./docs/images/AILegalAssistant.gif)

#### Single Question Evaluation

![Single Question RAG Evaluation](./docs/images/single_evaluation.gif)
_Real-time evaluation of individual questions showing accuracy, relevance, and groundedness metrics_

### Key Capabilities

- **Document Analysis**: Upload and analyze legal documents (PDFs, text files)
- **Intelligent Q&A**: Ask complex legal questions and get contextual answers
- **Hybrid Search**: Combines semantic vector search with keyword-based retrieval
- **Source Attribution**: Every answer includes citations to source documents
- **Real-time Streaming**: Responses stream in real-time for better UX
- **Cost Monitoring**: Track OpenAI API usage and costs
- **Performance Analytics**: Monitor response times and system performance

## ✨ Features

### 🔍 Advanced Retrieval System

- **Hybrid Search**: Ensemble retriever combining BM25 and semantic search
- **Smart Reranking**: Advanced document scoring for relevance
- **Query Preprocessing**: Automatic query enhancement and expansion
- **Metadata Filtering**: Filter documents by type, date, or custom attributes

### 🔐 Enterprise-Ready Security

- **Authentication System**: JWT-based user authentication
- **Rate Limiting**: Configurable API rate limits with Redis backing
- **Input Validation**: Comprehensive request validation and sanitization

### 📊 Monitoring & Analytics

- **Cost Tracking**: Real-time OpenAI API usage and cost monitoring
- **Latency Metrics**: Detailed performance tracking with TTFT (Time to First Token)
- **Evaluation Framework**: Built-in RAG evaluation with multiple metrics

### 🚀 Scalable Architecture

- **FastAPI Backend**: High-performance async Python API
- **React Frontend**: Modern, responsive user interface
- **Vector Database**: ChromaDB for efficient similarity search
- **Caching Layer**: Redis for performance optimization

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Frontend"
        UI[React + TypeScript UI]
        UI --> API[FastAPI Backend]
    end

    subgraph "Backend Services"
        API --> Auth[Authentication Service]
        API --> Chat[Enhanced Chat Service]
        API --> Eval[Evaluation Service]
        API --> Cache[Redis Cache]
    end

    subgraph "Data Layer"
        Chat --> Retriever[Hybrid Retriever]
        Retriever --> Vector[ChromaDB Vector Store]
        Retriever --> BM25[BM25 Keyword Search]
        Chat --> LLM[OpenAI GPT Models]
    end

    subgraph "Monitoring"
        API --> Cost[Cost Tracking]
        API --> Latency[Latency Metrics]
        API --> Health[Health Checks]
    end

    subgraph "AWS Infrastructure"
        S3[Document Storage]
        RDS[PostgreSQL Database]
        ElastiCache[Redis Cache]
        Secrets[Secrets Manager]
    end
```

## 🛠️ Technology Stack

### Backend

- **FastAPI** - Modern, fast web framework for building APIs
- **LangChain** - Framework for developing LLM applications
- **OpenAI API** - GPT models for natural language processing
- **ChromaDB** - Vector database for semantic search
- **Redis** - In-memory data structure store for caching
- **PostgreSQL** - Production database (AWS RDS)
- **SQLite** - Development database

### Frontend

- **React 19** - User interface library
- **TypeScript** - Typed JavaScript for better development
- **Vite** - Fast build tool and development server
- **TailwindCSS** - Utility-first CSS framework
- **React Query** - Data fetching and state management
- **Framer Motion** - Animation library

### Infrastructure

- **Local Development** - SQLite database for development
- **Redis** - Local caching and rate limiting

### AI/ML Stack

- **OpenAI GPT-4** - Large language model for generation
- **sentence-transformers** - Embedding models for semantic search
- **scikit-learn** - Machine learning utilities
- **BM25** - Keyword-based retrieval algorithm

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/ai-legal-assistant.git
   cd ai-legal-assistant
   ```

2. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key and other configurations
   ```

3. **Run with Docker Compose**

   ```bash
   cd backend
   docker-compose up -d
   ```

4. **Access the application**
   - API Documentation: http://localhost:8000/docs
   - Frontend: http://localhost:3000 (if configured)

## 💻 Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (for caching)
- PostgreSQL (for production)

### Backend Setup

1. **Create Python virtual environment**

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your configuration:

   ```env
   # Required
   OPENAI_API_KEY=your_openai_api_key_here

   # Optional - Database
   DATABASE_URL=sqlite:///./ai_legal_assistant.db

   # Optional - Redis (for caching)
   REDIS_URL=redis://localhost:6379
   ```

### Frontend Setup

1. **Install dependencies**

   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**

   ```bash
   npm run dev
   ```

3. **Build for production**
   ```bash
   npm run build
   ```

## ⚙️ Configuration

### Environment Variables

| Variable            | Description                   | Default                  | Required |
| ------------------- | ----------------------------- | ------------------------ | -------- |
| `OPENAI_API_KEY`    | OpenAI API key for GPT models | -                        | ✅       |
| `ENVIRONMENT`       | Deployment environment        | `development`            | ❌       |
| `DATABASE_URL`      | Database connection string    | SQLite local             | ❌       |
| `REDIS_URL`         | Redis connection string       | `redis://localhost:6379` | ❌       |
| `LANGSMITH_API_KEY` | LangSmith tracing API key     | -                        | ❌       |

### Advanced Configuration

#### Rate Limiting

Configure in `backend/config/rate_limits.py`:

```python
RATE_LIMITS = {
    "chat": "10/minute",
    "evaluation": "5/minute",
    "upload": "3/minute"
}
```

#### Cost Monitoring

Set spending limits in `backend/config/cost_limits.py`:

```python
COST_LIMITS = {
    "daily_limit": 100.0,  # USD
    "monthly_limit": 1000.0,  # USD
    "per_request_limit": 5.0  # USD
}
```

## 🎮 Usage

### Basic Q&A

```python
# Example API request
POST /chat/enhanced
{
    "message": "What are the key provisions of contract termination?",
    "user_id": "user123",
    "session_id": "session456",
    "stream": true
}
```

### Document Upload

```python
# Upload legal documents
POST /documents/upload
{
    "file": "contract.pdf",
    "metadata": {
        "type": "contract",
        "date": "2024-01-01",
        "category": "employment"
    }
}
```

### Evaluation

```python
# Run evaluation on test dataset
POST /evaluation/run
{
    "dataset_name": "legal_qa_test",
    "metrics": ["accuracy", "relevance", "completeness"]
}
```

## 📚 API Documentation

### Chat Endpoints

- `POST /chat/enhanced` - Enhanced chat with RAG
- `GET /chat/history/{session_id}` - Get chat history
- `DELETE /chat/sessions/{session_id}` - Clear session

### Document Management

- `POST /documents/upload` - Upload documents
- `GET /documents/` - List documents
- `DELETE /documents/{document_id}` - Delete document

### Evaluation & Analytics

- `POST /evaluation/run` - Run evaluation
- `GET /evaluation/results/{run_id}` - Get evaluation results
- `GET /metrics/latency` - Get latency metrics
- `GET /metrics/costs` - Get cost analytics

### Administration

- `POST /cache/clear` - Clear cache
- `GET /admin/stats` - System statistics

Full API documentation available at `/docs` when running the server.

## � Data Persistence

### Local Development Setup

The application uses local file storage for development:

- **Vector Database**: ChromaDB stores embeddings locally in `backend/chroma_db/`
- **Application Database**: SQLite database for user sessions and metrics
- **Document Storage**: Local file system in `backend/documents/`
- **Cache**: Local Redis instance for rate limiting and caching

### Data Backup

To backup your local data:

```bash
# Backup vector database
cp -r backend/chroma_db/ backup/chroma_db_$(date +%Y%m%d)/

# Backup SQLite database
cp backend/ai_legal_assistant.db backup/db_$(date +%Y%m%d).db

# Backup documents
cp -r backend/documents/ backup/documents_$(date +%Y%m%d)/
```

## 📊 Monitoring & Analytics

### Built-in Metrics

- **Response Time**: TTFT (Time to First Token) and total response time
- **Cost Tracking**: Real-time OpenAI API usage and costs
- **Error Rates**: Track and analyze system errors
- **Cache Performance**: Redis cache hit/miss ratios

### Evaluation Framework

The system includes a comprehensive evaluation framework:

![Batch Evaluation Dashboard](./docs/images/batch_evaluation.png)
_Comprehensive batch evaluation dashboard showing detailed metrics across multiple test cases_

```python
# Run evaluation
evaluator = RAGEvaluator(
    retriever=enhanced_retriever,
    llm=ChatOpenAI(),
    metrics=["accuracy", "relevance", "completeness", "groundedness"]
)

results = evaluator.evaluate(test_dataset)
```

### Available Metrics

- **Accuracy**: How often the answer is factually correct
- **Relevance**: How well the answer addresses the question
- **Completeness**: How comprehensive the answer is
- **Groundedness**: How well the answer is supported by sources
- **Latency**: Response time metrics

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest backend/tests/`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- Python: Follow PEP 8, use Black formatter
- TypeScript: Follow Airbnb style guide, use Prettier
- Commit messages: Follow Conventional Commits

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Key Issues**

   ```bash
   # Verify API key is set
   echo $OPENAI_API_KEY

   # Test API connectivity
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
        https://api.openai.com/v1/models
   ```

2. **Vector Database Issues**

   ```bash
   # Clear ChromaDB if corrupted
   rm -rf backend/chroma_db/*

   # Rebuild vector database
   python backend/scripts/rebuild_vectordb.py
   ```

3. **Redis Connection Issues**

   ```bash
   # Check Redis status
   redis-cli ping

   # Clear Redis cache
   redis-cli FLUSHALL
   ```

### Performance Optimization

- Use Redis caching for frequently accessed documents
- Implement query result caching
- Optimize embedding model size based on accuracy needs
- Use async processing for document ingestion

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com) for the RAG framework
- [OpenAI](https://openai.com) for the GPT models
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework

## 📞 Support

For questions and support:

- 📧 Email: support@ai-legal-assistant.com
- 💬 Discord: [Join our community](https://discord.gg/ai-legal-assistant)
- 📖 Documentation: [docs.ai-legal-assistant.com](https://docs.ai-legal-assistant.com)
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/ai-legal-assistant/issues)

---

⭐ If you find this project helpful, please consider giving it a star on GitHub!
