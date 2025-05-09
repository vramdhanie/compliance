#!/usr/bin/env python
"""
Example script demonstrating question answering with user feedback
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import (
    DocumentStorage, 
    VectorStore, 
    QAStorage, 
    QAVectorStore
)
from app.services import DocumentQA, FeedbackService


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


def print_answer(result: Dict[str, Any]) -> None:
    """Print the answer and its sources"""
    print("\n" + "="*80)
    print("ANSWER:")
    print("-"*80)
    print(f"{result['answer']}")
    print("-"*80)
    
    if result.get("from_cache", False):
        print("\nThis answer was retrieved from a previously validated Q&A pair")
        print(f"Original question: {result.get('original_question', '')}")
        print(f"Similarity score: {result.get('similarity', 0):.2f}")
    
    print("\nSOURCES:")
    for source in result.get("sources", []):
        print(f"  - {source.get('source', 'Unknown')} ({source.get('relevance', 'unknown')})")
    print("="*80 + "\n")


def process_feedback(qa_service: DocumentQA, result: Dict[str, Any]) -> Dict[str, Any]:
    """Process user feedback on the answer"""
    qa_id = result.get("qa_id", "")
    if not qa_id:
        print("Error: No QA ID found in the result. Cannot process feedback.")
        return result
        
    if get_yes_no_input("Is this answer accurate and helpful?"):
        # Positive feedback
        print("Great! Thanks for your feedback.")
        qa_service.collect_feedback(qa_id, True)
        return result
    
    # Negative feedback
    exit_loop = False
    current_result = result
    context_chunks = result.get("context_chunks", [])
    
    while not exit_loop:
        feedback = get_user_input("Please describe what issues you found with the answer")
        
        if feedback.lower() in ["exit", "quit", "q"]:
            print("Exiting feedback loop without saving.")
            return current_result
            
        # Save the negative feedback
        qa_service.collect_feedback(qa_id, False, feedback)
        
        # Try to generate a better answer
        print("\nGenerating an improved answer based on your feedback...")
        improved_result = qa_service.retry_answer(
            result.get("question", ""),
            feedback,
            context_chunks
        )
        
        # Print the improved answer
        print_answer(improved_result)
        
        # Check if this answer is better
        if get_yes_no_input("Is this improved answer satisfactory?"):
            print("Great! Thanks for helping improve the answer.")
            # Store this as a new QA pair
            new_qa_id = qa_service.feedback_service.store_qa_pair(
                result.get("question", ""),
                improved_result["answer"],
                improved_result["sources"]
            )
            # Mark it as validated
            qa_service.collect_feedback(new_qa_id, True)
            return improved_result
        
        # Ask if they want to try again or exit
        if not get_yes_no_input("Would you like to provide additional feedback and try again?"):
            print("Exiting feedback loop.")
            exit_loop = True
            
        current_result = improved_result
    
    return current_result


def interactive_qa_loop(qa_service: DocumentQA) -> None:
    """Interactive Q&A loop with feedback collection"""
    print("Welcome to the Interactive Q&A System!")
    print("Ask questions about your documents and provide feedback to improve answers.")
    print("Type 'exit' or 'quit' to end the session.")
    
    while True:
        # Get the user's question
        question = get_user_input("\nEnter your question")
        
        if question.lower() in ["exit", "quit", "q"]:
            print("Thank you for using the Interactive Q&A System. Goodbye!")
            break
        
        # Get the answer
        result = qa_service.interactive_qa(question)
        
        # Add the question to the result for reference
        result["question"] = question
        
        # Print the answer
        print_answer(result)
        
        # Process feedback if needed
        if result.get("requires_feedback", False):
            process_feedback(qa_service, result)


def main():
    """Main function"""
    # Initialize storage
    doc_storage = DocumentStorage()
    vector_store = VectorStore()
    qa_storage = QAStorage()
    qa_vector_store = QAVectorStore()
    
    # Initialize feedback service
    feedback_service = FeedbackService(qa_storage, qa_vector_store)
    
    # Initialize QA service
    qa_service = DocumentQA(
        mongo_storage=doc_storage,
        vector_store=vector_store,
        feedback_service=feedback_service
    )
    
    # Start interactive QA loop
    interactive_qa_loop(qa_service)


if __name__ == "__main__":
    main() 