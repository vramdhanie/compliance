import os
import argparse
import glob
import json
import dotenv
import re
from app.utils.document_parser import DocumentParser
from app.utils.text_processor import TextProcessor
from app.database.documents import DocumentStorage
from app.database.vector_store import VectorStore
from app.database.qa_storage import QAStorage
from app.database.qa_vector_store import QAVectorStore
from app.services.question_service import DocumentQA
from app.services.feedback_service import FeedbackService

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
    query_parser.add_argument("--no-feedback", action="store_true",
                             help="Skip the feedback collection process")
    
    # List documents command
    list_parser = subparsers.add_parser("list", help="List ingested documents")
    list_parser.add_argument("--concepts", action="store_true",
                            help="List all concepts instead of documents")
    list_parser.add_argument("--qa-pairs", action="store_true",
                            help="List validated QA pairs instead of documents")
    
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
    qa_storage = QAStorage()
    qa_vector_store = QAVectorStore()
    
    # Initialize feedback service
    feedback_service = FeedbackService(qa_storage, qa_vector_store)
    
    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_endpoint = os.getenv("OPENAI_ENDPOINT")
    openai_deployment = os.getenv("OPENAI_DEPLOYMENT_NAME")
    
    if not openai_api_key:
        print("Warning: OPENAI_API_KEY not found in environment variables or .env file")
    
    # Initialize QA system
    qa_system = DocumentQA(
        mongo_storage=mongo_storage, 
        vector_store=vector_store, 
        api_key=openai_api_key,
        endpoint=openai_endpoint,
        deployment_name=openai_deployment,
        feedback_service=feedback_service
    )
    
    return qa_system, mongo_storage, vector_store, qa_storage

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

def get_user_input(prompt: str) -> str:
    """Get input from the user with the specified prompt"""
    return input(f"{prompt}: ")

def get_yes_no_input(prompt: str) -> bool:
    """Get a yes/no response from the user"""
    while True:
        response = input(f"{prompt} (yes/no): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        print("Please enter 'yes' or 'no'")

def print_answer(result):
    """Print the answer and its sources"""
    print("\n" + "="*80)
    print("ANSWER:")
    print("-"*80)
    
    # Check for invalid citations in the answer
    answer = result["answer"]
    citation_pattern = r'\[Document (\d+)\]'
    citations_in_text = [int(doc_num) for doc_num in re.findall(citation_pattern, answer)]
    
    # Get citation numbers that appear in the text
    valid_citation_nums = set()
    for source in result.get("sources", []):
        if source.get("relevance") == "cited":
            # Extract the document number from the source if possible
            source_name = source.get("source", "")
            match = re.search(r'Document (\d+)', source_name)
            if match:
                valid_citation_nums.add(int(match.group(1)))
    
    # Check for citations in text that aren't in sources
    invalid_citations = []
    for citation in citations_in_text:
        if citation not in valid_citation_nums:
            invalid_citations.append(citation)
    
    if invalid_citations:
        # Highlight invalid citations in the answer
        for citation in invalid_citations:
            answer = answer.replace(f"[Document {citation}]", f"[Document {citation}] (CITATION NOT FOUND)")
    
    print(answer)
    print("-"*80)
    
    if invalid_citations:
        print("\nWARNING: Found citations in the answer that don't match available sources!")
        print(f"Invalid citation numbers: {', '.join(str(c) for c in invalid_citations)}")
    
    if result.get("is_retry", False):
        print("\nThis is an improved answer based on your feedback.")
    elif result.get("from_cache", False):
        print("\nThis answer was retrieved from a previously validated Q&A pair")
        print(f"Original question: {result.get('original_question', '')}")
        print(f"Similarity score: {result.get('similarity', 0):.2f}")
    
    print("\nSOURCES:")
    if not result.get("sources"):
        print("  No sources available")
    else:
        for i, source in enumerate(result.get("sources", [])):
            relevance = "[Cited]" if source.get("relevance") == "cited" else "[Relevant]"
            print(f"{i+1}. {relevance} {source.get('source', 'Unknown')} ({source.get('type', 'Unknown')})")
    print("="*80 + "\n")

def process_feedback(qa_system, result):
    """Process user feedback on the answer"""
    qa_id = result.get("qa_id", "")
    if not qa_id:
        print("Error: No QA ID found in the result. Cannot process feedback.")
        return result
        
    if get_yes_no_input("Is this answer accurate and helpful?"):
        # Positive feedback
        print("Great! Thanks for your feedback.")
        qa_system.collect_feedback(qa_id, True)
        return result
    
    # Negative feedback
    exit_loop = False
    current_result = result
    
    while not exit_loop:
        feedback = get_user_input("Please describe what issues you found with the answer")
        
        if feedback.lower() in ["exit", "quit", "q"]:
            print("Exiting feedback loop without saving.")
            return current_result
            
        # Save the negative feedback
        qa_system.collect_feedback(qa_id, False, feedback)
        
        # Try to generate a better answer using DocumentQA's retry_answer
        print("\nGenerating an improved answer based on your feedback...")
        improved_result = qa_system.retry_answer(
            current_result.get("question", ""),
            feedback,
            current_result.get("context_chunks", [])
        )
        
        # Make sure the question is preserved in the improved result
        improved_result["question"] = current_result.get("question", "")
        
        # Print the improved answer
        print_answer(improved_result)
        
        # Check if this answer is better
        if get_yes_no_input("Is this improved answer satisfactory?"):
            print("Great! Thanks for helping improve the answer.")
            # Store this as a new QA pair
            if qa_system.feedback_service:
                new_qa_id = qa_system.feedback_service.store_qa_pair(
                    current_result.get("question", ""),
                    improved_result["answer"],
                    improved_result["sources"]
                )
                # Mark it as validated
                qa_system.collect_feedback(new_qa_id, True)
            return improved_result
        
        # Ask if they want to try again or exit
        if not get_yes_no_input("Would you like to provide additional feedback and try again?"):
            print("Exiting feedback loop.")
            exit_loop = True
            
        current_result = improved_result
    
    return current_result

def ask_question(qa_system, question, n_results, file_type=None, collect_feedback=True):
    """Ask a question and get an answer with optional feedback collection"""
    # Prepare filters
    filters = {}
    if file_type:
        filters["type"] = file_type
    
    print(f"\nQuestion: {question}")
    print("Searching for relevant information...")
    
    # Get answer (with feedback enabled if requested)
    result = qa_system.answer_question(
        question=question,
        n_results=n_results,
        filters=filters,
        collect_feedback=collect_feedback
    )
    
    # Add the question to the result for reference
    result["question"] = question
    
    # Print the answer
    print_answer(result)
    
    # Process feedback if needed and requested
    if collect_feedback and result.get("qa_id"):
        process_feedback(qa_system, result)
    elif result.get("from_cache", False):
        print("This answer was retrieved from a previously validated Q&A pair.")
        print(f"Original question: {result.get('original_question', '')}")
        print(f"Similarity score: {result.get('similarity', 0):.2f}")

def list_documents(mongo_storage, qa_storage=None, list_concepts=False, list_qa_pairs=False):
    """List all ingested documents, concepts, or QA pairs"""
    if list_qa_pairs and qa_storage:
        # List all validated QA pairs
        qa_pairs = qa_storage.get_all_qa_pairs(validated_only=True)
        if not qa_pairs:
            print("No validated QA pairs found in the database")
            return
        
        print(f"Found {len(qa_pairs)} validated QA pairs:")
        for i, qa in enumerate(qa_pairs):
            print(f"{i+1}. Q: {qa.get('question', 'Unknown')[:80]}...")
            print(f"   ID: {qa.get('qa_id', 'Unknown')}")
            print()
    elif list_concepts:
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
    qa_system, mongo_storage, vector_store, qa_storage = setup_system()
    
    # Execute command
    if args.command == "ingest":
        ingest_documents(qa_system, args.path, args.chunk_size, args.chunk_overlap)
    elif args.command == "query":
        ask_question(qa_system, args.question, args.results, args.file_type, not args.no_feedback)
    elif args.command == "list":
        list_documents(mongo_storage, qa_storage, args.concepts, args.qa_pairs)
    elif args.command == "get":
        get_document(mongo_storage, args.id)
    else:
        print("Please specify a command: ingest, query, list, or get")
        print("Use --help for more information")

if __name__ == "__main__":
    main()