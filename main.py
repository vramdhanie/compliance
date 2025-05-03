import os
import argparse
import glob
import json
import dotenv
from app.utils.document_parser import DocumentParser
from app.utils.text_processor import TextProcessor
from app.database.documents import DocumentStorage
from app.database.vector_store import VectorStore
from app.services.question_service import DocumentQA

# Load environment variables
dotenv.load_dotenv()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Document QA System")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Ingest documents command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents into the system")
    ingest_parser.add_argument("--path", type=str, required=True, 
                              help="Path to document(s). Can be a file or directory")
    ingest_parser.add_argument("--chunk-size", type=int, default=1000,
                              help="Size of text chunks in characters")
    ingest_parser.add_argument("--chunk-overlap", type=int, default=200,
                              help="Overlap between chunks in characters")
    
    # Ask question command
    query_parser = subparsers.add_parser("query", help="Ask a question")
    query_parser.add_argument("--question", type=str, required=True,
                             help="Question to answer")
    query_parser.add_argument("--results", type=int, default=5,
                             help="Number of results to retrieve")
    query_parser.add_argument("--file-type", type=str,
                             help="Filter results by file type")
    
    # List documents command
    list_parser = subparsers.add_parser("list", help="List ingested documents")
    list_parser.add_argument("--concepts", action="store_true",
                            help="List all concepts instead of documents")
    
    # Get document command
    get_parser = subparsers.add_parser("get", help="Get a specific document")
    get_parser.add_argument("--id", type=str, required=True,
                           help="Document ID to retrieve")
    
    return parser.parse_args()

def setup_system():
    """Set up the document QA system"""
    # Initialize components
    mongo_storage = DocumentStorage()
    vector_store = VectorStore()
    
    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Warning: OPENAI_API_KEY not found in environment variables or .env file")
    
    # Initialize QA system
    qa_system = DocumentQA(mongo_storage, vector_store, openai_api_key)
    
    return qa_system, mongo_storage, vector_store

def ingest_documents(qa_system, path, chunk_size, chunk_overlap):
    """Ingest documents from the specified path"""
    parser = DocumentParser()
    processor = TextProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # Get file paths
    if os.path.isdir(path):
        file_paths = []
        # Get all supported file types
        for ext in [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt", ".json", ".html", ".htm"]:
            file_paths.extend(glob.glob(os.path.join(path, f"**/*{ext}"), recursive=True))
    else:
        file_paths = [path]
    
    if not file_paths:
        print(f"No supported files found at: {path}")
        return
    
    print(f"Found {len(file_paths)} files to process")
    
    # Process documents
    results = qa_system.process_documents(file_paths, parser, processor)
    
    # Print results
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"Successfully processed {success_count} out of {len(results)} files")
    
    for result in results:
        if result["status"] == "success":
            print(f"✓ {result['file']} - {result['chunks']} chunks")
        else:
            print(f"✗ {result['file']} - Error: {result['error']}")

def ask_question(qa_system, question, n_results, file_type=None):
    """Ask a question and get an answer"""
    # Prepare filters
    filters = {}
    if file_type:
        filters["type"] = file_type
    
    print(f"\nQuestion: {question}")
    print("Searching for relevant information...")
    
    # Get answer
    result = qa_system.answer_question(question, n_results=n_results, filters=filters)
    
    # Print answer
    print("\n" + "="*50)
    print("Answer:")
    print(result["answer"])
    print("\n" + "="*50)
    print("Sources:")
    
    for i, source in enumerate(result["sources"]):
        relevance = "[Cited]" if source["relevance"] == "cited" else "[Relevant]"
        print(f"{i+1}. {relevance} {source['source']} ({source['type']})")

def list_documents(mongo_storage, list_concepts=False):
    """List all ingested documents or concepts"""
    if list_concepts:
        # List all concepts
        concepts = mongo_storage.get_all_concepts()
        if not concepts:
            print("No concepts found in the database")
            return
        
        print(f"Found {len(concepts)} concepts:")
        for i, concept_obj in enumerate(concepts):
            print(f"{i+1}. {concept_obj['concept']}")
    else:
        # List all documents
        documents = list(mongo_storage.documents.find({}, {
            "document_id": 1, 
            "title": 1, 
            "metadata.type": 1,
            "metadata.source": 1,
        }))
        
        if not documents:
            print("No documents found in the database")
            return
        
        print(f"Found {len(documents)} documents:")
        for i, doc in enumerate(documents):
            doc_type = doc.get("metadata", {}).get("type", "unknown")
            source = doc.get("metadata", {}).get("source", "unknown")
            print(f"{i+1}. [{doc_type}] {doc.get('title', source)} - ID: {doc['document_id']}")

def get_document(mongo_storage, document_id):
    """Get details for a specific document"""
    doc = mongo_storage.get_document(document_id)
    if not doc:
        print(f"Document not found with ID: {document_id}")
        return
    
    # Print document details
    print(f"Document: {doc.get('title', doc['document_id'])}")
    print(f"Type: {doc.get('metadata', {}).get('type', 'unknown')}")
    print(f"Source: {doc.get('metadata', {}).get('source', 'unknown')}")
    
    if "concepts" in doc and doc["concepts"]:
        print("\nConcepts:")
        for i, concept in enumerate(doc["concepts"]):
            print(f"  {i+1}. {concept}")
    
    if "summary" in doc and doc["summary"]:
        print("\nSummary:")
        print(doc["summary"])
    
    # Get chunks
    chunks = mongo_storage.get_chunks_by_document(document_id)
    print(f"\nChunks: {len(chunks)}")
    
    # Print first few chunks
    max_chunks_to_show = 3
    for i, chunk in enumerate(chunks[:max_chunks_to_show]):
        print(f"\nChunk {i+1}/{len(chunks)}:")
        
        # Truncate content if too long
        content = chunk["content"]
        if len(content) > 200:
            content = content[:200] + "..."
        
        print(content)
    
    if len(chunks) > max_chunks_to_show:
        print(f"\n... {len(chunks) - max_chunks_to_show} more chunks not shown ...")

def main():
    """Main entry point"""
    # Parse arguments
    args = parse_arguments()
    
    # Set up system
    qa_system, mongo_storage, vector_store = setup_system()
    
    # Execute command
    if args.command == "ingest":
        ingest_documents(qa_system, args.path, args.chunk_size, args.chunk_overlap)
    elif args.command == "query":
        ask_question(qa_system, args.question, args.results, args.file_type)
    elif args.command == "list":
        list_documents(mongo_storage, args.concepts)
    elif args.command == "get":
        get_document(mongo_storage, args.id)
    else:
        print("Please specify a command: ingest, query, list, or get")
        print("Use --help for more information")

if __name__ == "__main__":
    main()