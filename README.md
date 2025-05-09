# Compliance Document Management System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.4%2B-green)](https://www.mongodb.com/)
[![TypeChecking: MyPy](https://img.shields.io/badge/type%20checking-mypy-blue)](http://mypy-lang.org/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A powerful document management system designed for regulatory compliance, using MongoDB for document storage and Azure OpenAI for intelligent document analysis and question answering.

## Overview

This application helps organizations manage, analyze, and extract insights from compliance-related documents. It combines robust document storage with advanced AI capabilities to provide:

- **Intelligent Document Storage**: Store and organize documents with automatic metadata extraction
- **Semantic Search**: Find relevant document sections using natural language queries
- **Document Q&A**: Ask questions about your compliance documents and get accurate answers with citations
- **Document Analysis**: Extract key concepts, entities, and relationships from documents
- **Vector-based Similarity**: Find similar documents and concepts using embedded vector representations
- **Table Parsing**: Automatically detect and parse tabular compliance data

The system uses MongoDB for document storage and Azure OpenAI for AI capabilities, with a modular architecture that allows for flexible deployment and scaling.

## Key Features

- **Document Processing Pipeline**: Parse various document formats (PDF, DOCX, CSV, etc.)
- **Smart Chunking**: Break documents into semantic chunks for better retrieval
- **Table Detection**: Automatically identify and parse tabular compliance data
- **Vector Embeddings**: Store document embeddings for semantic similarity search
- **MongoDB Integration**: Scalable document storage with full-text search capabilities
- **Azure OpenAI Integration**: Advanced LLM capabilities for document understanding
- **Type-Safe Codebase**: Fully type-annotated Python with MyPy support
- **Modular Architecture**: Easily extensible with new document types and features

## Project Structure

```
compliance/
├── app/
│   ├── __init__.py         # Main package initialization
│   ├── config/             # Configuration settings
│   │   ├── __init__.py
│   │   └── env.py
│   ├── database/           # Database connection and models
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── documents.py    # Document storage models
│   │   ├── vector_store.py # Vector embedding storage
│   │   ├── test_connection.py
│   │   └── types.py
│   ├── schemas/            # Data validation and normalization
│   │   ├── __init__.py
│   │   ├── document.py     # Document schema definitions
│   │   └── user.py
│   ├── services/           # Business logic
│   │   ├── __init__.py
│   │   ├── question_service.py # Document Q&A service
│   │   └── document_service.py # Document processing service
│   └── utils/              # Utility functions
│       ├── __init__.py
│       └── text_processor.py # Document chunking and processing
├── scripts/                # Utility scripts
│   ├── setup_uv.sh         # Setup script for Unix/macOS
│   └── setup_uv.bat        # Setup script for Windows
├── main.py                 # Application entry point
├── requirements.txt        # Project dependencies
├── requirements-dev.txt    # Development dependencies
├── setup.py                # Package installation script
├── mypy.ini                # Type checking configuration
└── README.md               # Project documentation
```

## Prerequisites

- Python 3.11 or higher
- MongoDB running locally or accessible via connection string
- Azure OpenAI API access
- uv package manager (recommended)

## Installation

### Using the Setup Scripts (Recommended)

The easiest way to set up the project is to use the provided setup scripts:

**On Unix/macOS:**
```bash
./scripts/setup_uv.sh
```

**On Windows:**
```bash
scripts\setup_uv.bat
```

This will:
1. Install uv if not already installed
2. Create a virtual environment
3. Install dependencies and development dependencies
4. Install the package in development mode

### Using uv Manually

If you prefer to set up manually:

1. Install uv if you haven't already:
   ```bash
   pip install uv
   ```

2. Create and activate a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```

3. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```

4. For development, install additional dependencies:
   ```bash
   uv pip install -r requirements-dev.txt
   ```

5. Install the package in development mode:
   ```bash
   uv pip install -e .
   ```

### Using pip

Alternatively, you can use pip:

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Configuration

The application uses the following environment variables:

### Required
- `OPENAI_API_KEY`: Azure OpenAI API key
- `OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `OPENAI_DEPLOYMENT_NAME`: Azure OpenAI model deployment name

### Optional
- `MONGO_URI`: MongoDB connection string (default: `mongodb://localhost:27017`)
- `MONGO_DB`: MongoDB database name (default: `compliance_db`)
- `DEBUG`: Enable debug mode (default: `False`)
- `ENVIRONMENT`: Application environment (default: `development`)

You can set these variables in a `.env` file in the project root (see `env.example`).

## Usage

### Running the Application

```bash
python main.py
```

### Document Processing and Storage

```python
from app.database import DocumentStorage, VectorStore
from app.services.question_service import DocumentQA
from app.utils.text_processor import TextProcessor

# Initialize storage
doc_storage = DocumentStorage()
vector_store = VectorStore()

# Initialize text processor and QA service
text_processor = TextProcessor(chunk_size=1000, chunk_overlap=200)
qa_service = DocumentQA(doc_storage, vector_store)

# Process documents
results = qa_service.process_documents(
    ["path/to/document1.pdf", "path/to/document2.docx", "path/to/compliance_table.txt"],
    parser,
    text_processor
)

# Ask questions about your documents
answer = qa_service.answer_question(
    "What are the key compliance requirements for Identity & Access Management?",
    n_results=5
)

print(answer["answer"])
# Access source information
for source in answer["sources"]:
    print(f"Source: {source['source']}, Relevance: {source['relevance']}")
```

### Table Parsing

The system can automatically detect and parse compliance tables in this format:

```
1 | Identity & Access Management | YES | Sybill uses Role-Based Access Control and the principle of least privilege... | access-control-policy
2 | Data Protection | PARTIAL | Encryption is implemented for data in transit, but at-rest encryption... | data-protection-policy
```

Each table row is stored as a separate chunk with structured metadata:

```python
# Retrieve documents with tabular data
tabular_docs = doc_storage.find_chunks_by_metadata({"is_table_row": True})

# Filter by compliance category
identity_controls = doc_storage.find_chunks_by_metadata({
    "is_table_row": True,
    "control_category": "Identity & Access Management"
})

# Find all fully compliant controls
compliant_controls = doc_storage.find_chunks_by_metadata({
    "is_table_row": True,
    "compliance_status": "YES"
})
```

### Getting Structured JSON Responses

```python
# Define a schema for the response
schema = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {"type": "string"}
        },
        "citations": {
            "type": "array",
            "items": {"type": "integer"}
        }
    }
}

# Get a structured response
result = qa_service.answer_question(
    "What are the key compliance requirements for data protection?",
    n_results=5,
    json_response=True,
    json_schema=schema
)
```

## Using the Database Module

To use the MongoDB connection in other parts of your application:

```python
# Import the db instance
from app.database import db

# Get a collection
collection = db.get_collection("your_collection_name")

# Perform operations
collection.insert_one({"key": "value"})
documents = collection.find({"key": "value"})

# Close connection when done (typically at application exit)
db.close()
```

## Development

### Type Checking

The project includes type annotations and can be type-checked using mypy:

```bash
mypy app
```

### Running Tests

```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
