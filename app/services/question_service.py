import os
import json
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import re
from typing import Dict, List, Any, Optional, Union, cast, Literal, Tuple

from app.services.feedback_service import FeedbackService


class DocumentQA:
    """Question answering system for documents using vector search and LLM"""
    
    def __init__(self, mongo_storage, vector_store, api_key=None, endpoint=None, deployment_name=None, feedback_service=None):
        """Initialize the QA system with storage and LLM components"""
        self.mongo_storage = mongo_storage
        self.vector_store = vector_store
        self.feedback_service = feedback_service
        
        # Set up Azure OpenAI client with default fallbacks
        api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        endpoint = endpoint or os.getenv("OPENAI_ENDPOINT", "")
        self.deployment_name = deployment_name or os.getenv("OPENAI_DEPLOYMENT_NAME", "")
        
        if not api_key or not endpoint or not self.deployment_name:
            raise ValueError("Azure OpenAI API key, endpoint, and deployment name are required")
            
        self.openai_client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=endpoint
        )
        
        # Standard system message for all LLM interactions
        self.system_message = """You are a helpful assistant that provides accurate information based on the provided document context. 
        When answering the question:
        1. Use only information from the provided context.
        2. If the context doesn't contain relevant information, say that you don't have enough information to answer.
        3. Include citations in your answer using the format [Document X] where X is the document number from the context.
        4. Ensure that you ONLY cite document numbers that actually exist in the context (1 through N where N is the number of documents).
        5. DO NOT cite document numbers outside the range of available documents.
        6. Provide concise answers that directly address the question.
        7. When appropriate, include multiple citations to support your answer.
        8. Double-check all citations before providing your answer to ensure they are valid numbers.
        9. Be concise and to the point. Do not add extraneous information and statements.
        10. Speak in the first person, as if you are the one answering the question."""
    
    def process_documents(self, file_paths, parser, processor):
        """Process and store multiple documents"""
        results = []
        
        for file_path in file_paths:
            try:
                print(f"Processing {file_path}...")
                
                # Parse document
                doc = parser.parse_file(file_path)
                if not doc:
                    print(f"Failed to parse {file_path}")
                    continue
                
                # Process document into chunks
                doc_summary, chunks = processor.process_document(doc)
                
                # Store in MongoDB
                document_id = self.mongo_storage.store_document(doc_summary, chunks)
                
                # Add to vector store
                self.vector_store.add_chunks(chunks)
                
                results.append({
                    "file": file_path,
                    "document_id": document_id,
                    "chunks": len(chunks),
                    "status": "success"
                })
                
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
                results.append({
                    "file": file_path,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def answer_question(self, question: str, n_results: int = 5, filters: Optional[Dict[str, Any]] = None, 
                        json_response: bool = False, json_schema: Optional[Dict[str, Any]] = None,
                        collect_feedback: bool = False) -> Dict[str, Any]:
        """
        Answer a question using semantic search and LLM generation
        
        Args:
            question: The question to answer
            n_results: Number of relevant chunks to retrieve
            filters: Optional filters for the vector search
            json_response: Whether to request a JSON response from the LLM
            json_schema: Optional JSON schema to guide the LLM response format
            collect_feedback: Whether to collect user feedback on the answer
            
        Returns:
            Dict containing answer text and source information
        """
        # First, check if we have a similar question with validated answer
        similar_qa = None
        if self.feedback_service:
            similar_results = self.feedback_service.find_similar_questions(question, n_results=1, validated_only=True)
            if similar_results and len(similar_results) > 0 and similar_results[0].get("similarity", 0) > 0.85:
                similar_qa = similar_results[0]
        
        if similar_qa:
            # Use the existing answer if we have a highly similar question
            result = {
                "answer": similar_qa.get("full_answer", ""),
                "sources": similar_qa.get("sources", []),
                "from_cache": True,
                "similarity": similar_qa.get("similarity", 0),
                "original_question": similar_qa.get("question", ""),
                "qa_id": similar_qa.get("qa_id", "")
            }
            return result
        
        # Search for relevant chunks
        relevant_chunks = self.vector_store.search(question, n_results=n_results, filters=filters)
        
        if not relevant_chunks:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "sources": []
            }
        
        # Format context for the LLM
        context = self._format_context(relevant_chunks)
        
        # Remind the LLM about the document range
        user_message = f"""Question: {question}

Context:
{context}

Please provide a detailed answer {"in JSON format " if json_response else ""}with citations to the relevant documents. Remember to only cite document numbers that exist in the context (1 through {len(relevant_chunks)})."""
        
        # Generate answer with LLM
        answer, citations = self._generate_answer(
            question, 
            context, 
            relevant_chunks, 
            user_message=user_message,
            json_response=json_response, 
            json_schema=json_schema
        )
        
        # Format sources
        sources, invalid_citations = self._format_sources(relevant_chunks, citations)
        
        # Create the response
        result = {
            "answer": answer,
            "sources": sources,
            "from_cache": False,
            "context_chunks": relevant_chunks
        }
        
        if invalid_citations:
            result["has_invalid_citations"] = True
        
        # If feedback collection is enabled, store the Q&A pair
        if collect_feedback and self.feedback_service:
            qa_id = self.feedback_service.store_qa_pair(question, answer, sources)
            result["qa_id"] = qa_id
            
        return result
    
    def collect_feedback(self, qa_id: str, is_accurate: bool, feedback_text: Optional[str] = None) -> bool:
        """
        Collect user feedback on an answer
        
        Args:
            qa_id: The QA pair ID
            is_accurate: Whether the answer was accurate
            feedback_text: Optional feedback text
            
        Returns:
            bool: True if feedback was successfully saved
        """
        if not self.feedback_service:
            return False
            
        return self.feedback_service.add_feedback(qa_id, is_accurate, feedback_text)
    
    def retry_answer(self, question: str, feedback: str, previous_context: List[Dict[str, Any]], 
                     n_results: int = 5) -> Dict[str, Any]:
        """
        Retry answering a question based on user feedback
        
        Args:
            question: The original question
            feedback: User feedback on what was wrong with the previous answer
            previous_context: The previous context chunks
            n_results: Number of additional chunks to retrieve if needed
            
        Returns:
            Dict containing improved answer and source information
        """
        # Combine previous context with new chunks if needed
        context_chunks = previous_context
        
        # Get additional chunks if the feedback suggests more information is needed
        need_more_info = any(term in feedback.lower() for term in ["more info", "additional", "more context", "not enough", "incomplete"])
        
        if need_more_info:
            additional_chunks = self.vector_store.search(
                question, 
                n_results=n_results, 
                filters=None
            )
            
            # Combine with existing chunks, avoiding duplicates
            existing_ids = [chunk["chunk_id"] for chunk in context_chunks]
            for chunk in additional_chunks:
                if chunk["chunk_id"] not in existing_ids:
                    context_chunks.append(chunk)
        
        # Format combined context
        context = self._format_context(context_chunks)
        
        # User message with reminder about valid citation range
        user_message = f"""Question: {question}

Previous feedback: {feedback}

Context:
{context}

Please provide an improved answer that addresses the feedback, with citations to the relevant documents. Remember to only cite document numbers that exist in the context (1 through {len(context_chunks)})."""

        # Create properly typed messages
        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system", 
            "content": self.system_message
        }
        
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user", 
            "content": user_message
        }
        
        # Call the Azure OpenAI API
        response = self.openai_client.chat.completions.create(
            model=self.deployment_name,
            messages=[system_msg, user_msg],
            temperature=0.3,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        # Extract citations
        citation_pattern = r'\[Document (\d+)\]'
        citations = []
        if answer:
            citations = [int(doc_num) for doc_num in re.findall(citation_pattern, answer)]
        
        # Format sources
        sources, invalid_citations = self._format_sources(context_chunks, citations)
        
        # Create the response
        result = {
            "answer": answer or "",
            "sources": sources,
            "from_cache": False,
            "is_retry": True
        }
        
        if invalid_citations:
            result["has_invalid_citations"] = True
            
        return result
    
    def _format_context(self, chunks):
        """Format chunks into context for the LLM"""
        context_parts = []
        
        for i, chunk in enumerate(chunks):
            # Format metadata
            metadata = chunk["metadata"]
            source_info = f"Source: {metadata.get('source', 'Unknown')}"
            if "type" in metadata:
                source_info += f", Type: {metadata['type']}"
            
            # Add chunk with source info
            context_parts.append(f"[Document {i+1}] {source_info}\n{chunk['content']}")
        
        return "\n\n" + "\n\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str, chunks: List[Dict[str, Any]], 
                         user_message: Optional[str] = None,
                         json_response: bool = False, 
                         json_schema: Optional[Dict[str, Any]] = None) -> Tuple[Union[str, Dict[str, Any]], List[int]]:
        """
        Generate an answer using the LLM
        
        Args:
            question: User question
            context: Formatted context from document chunks
            chunks: Document chunks for citation extraction
            user_message: Optional custom user message (if None, a default one will be created)
            json_response: Whether to request a structured JSON response
            json_schema: Optional schema for the JSON response
            
        Returns:
            Tuple of (answer, citations) where answer is either a string or a JSON object
        """
        # Prepare system message with instructions for JSON responses
        system_message = self.system_message
        if json_response:
            system_message += """
            Your response must be valid JSON with the following structure:
            {
              "answer": "Your detailed answer here",
              "citations": [1, 2, ...] <- Document numbers from the context that support your answer
            }
            """
            
            if json_schema:
                schema_str = json.dumps(json_schema, indent=2)
                system_message += f"\nYour response must conform to this JSON schema:\n{schema_str}"
        
        # Use provided user message or create a default one
        if not user_message:
            user_message = f"""Question: {question}

Context:
{context}

Please provide a detailed answer {"in JSON format " if json_response else ""}with citations to the relevant documents. Remember to only cite document numbers that exist in the context (1 through {len(chunks)})."""

        # Create properly typed messages
        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system", 
            "content": system_message
        }
        
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user", 
            "content": user_message
        }
        
        # Call the Azure OpenAI API
        if json_response:
            response = self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[system_msg, user_msg],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
        else:
            response = self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[system_msg, user_msg],
                temperature=0.3,
                max_tokens=1000
            )
        
        answer = response.choices[0].message.content
        
        # Handle JSON response
        citations = []
        if json_response and answer:
            try:
                answer_json = json.loads(answer)
                # Extract citations from the JSON response
                if "citations" in answer_json and isinstance(answer_json["citations"], list):
                    citations = [int(citation) for citation in answer_json["citations"] if isinstance(citation, (int, str))]
                return answer_json, citations
            except json.JSONDecodeError:
                # Fall back to text response if JSON parsing fails
                pass
        
        # For text responses, extract citations from the text
        citation_pattern = r'\[Document (\d+)\]'
        if answer:
            citations = [int(doc_num) for doc_num in re.findall(citation_pattern, answer)]
        
        return answer or "", citations
    
    def _format_sources(self, chunks, citations) -> Tuple[List[Dict[str, Any]], List[int]]:
        """
        Format source information from chunks and citations
        
        Args:
            chunks: Document chunks
            citations: List of citation numbers
            
        Returns:
            Tuple of (sources, invalid_citations) where:
                - sources is a list of source objects
                - invalid_citations is a list of citation numbers that are out of range
        """
        sources = []
        cited_docs = set()
        invalid_citations = []
        
        # First add cited documents
        for citation in citations:
            if 1 <= citation <= len(chunks):
                chunk = chunks[citation-1]
                doc_id = chunk["metadata"].get("document_id")
                
                if doc_id and doc_id not in cited_docs:
                    cited_docs.add(doc_id)
                    sources.append({
                        "document_id": doc_id,
                        "source": f"Document {citation}: {chunk['metadata'].get('source', 'Unknown')}",
                        "type": chunk["metadata"].get("type", "Unknown"),
                        "relevance": "cited"
                    })
            else:
                invalid_citations.append(citation)
        
        # Then add other relevant but uncited documents
        for i, chunk in enumerate(chunks):
            doc_id = chunk["metadata"].get("document_id")
            if doc_id and doc_id not in cited_docs:
                cited_docs.add(doc_id)
                sources.append({
                    "document_id": doc_id,
                    "source": f"Document {i+1}: {chunk['metadata'].get('source', 'Unknown')}",
                    "type": chunk["metadata"].get("type", "Unknown"),
                    "relevance": "relevant"
                })
        
        return sources, invalid_citations
    
    def get_document_by_id(self, document_id):
        """Get a full document by ID"""
        doc = self.mongo_storage.get_document(document_id)
        if doc:
            # Fetch all chunks
            chunks = self.mongo_storage.get_chunks_by_document(document_id)
            doc["chunks"] = chunks
            return doc
        return None
        
    def interactive_qa(self, question: str, n_results: int = 5, filters: Optional[Dict[str, Any]] = None):
        """
        Interactive Q&A session with feedback collection
        
        Args:
            question: The user's question
            n_results: Number of relevant chunks to retrieve
            filters: Optional filters for the vector search
            
        Returns:
            Dict containing final answer and feedback information
        """
        # Get initial answer
        answer_result = self.answer_question(
            question=question,
            n_results=n_results,
            filters=filters,
            collect_feedback=True
        )
        
        # Record if this is from cache to avoid feedback loop
        if answer_result.get("from_cache", False):
            return answer_result
        
        # Process requires user feedback
        qa_id = answer_result.get("qa_id", "")
        if not qa_id:
            return answer_result
        
        # This would be handled by your application UI
        # Here we're just defining the protocol for integration
        
        # Steps in a real application:
        # 1. Display the answer to the user
        # 2. Prompt for feedback - "Is this answer accurate? (yes/no)"
        # 3. If yes:
        #    - Call self.collect_feedback(qa_id, True)
        #    - Return the answer
        # 4. If no:
        #    - Prompt for feedback text - "What issues did you find with the answer?"
        #    - Call self.collect_feedback(qa_id, False, feedback_text)
        #    - Generate a new answer with retry_answer()
        #    - Loop until user is satisfied or chooses to exit
        
        return {
            **answer_result,
            "requires_feedback": True
        }
        
    def validate_citations(self, answer: str) -> Tuple[List[int], List[int]]:
        """
        Extract citations from an answer and validate them against available chunks
        
        Args:
            answer: The answer text containing citations
            
        Returns:
            Tuple of (valid_citations, invalid_citations)
        """
        citation_pattern = r'\[Document (\d+)\]'
        all_citations = [int(doc_num) for doc_num in re.findall(citation_pattern, answer)]
        
        # Return empty lists as a basic implementation
        # In a real implementation, you would validate against available chunks
        return [], all_citations