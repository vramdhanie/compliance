import os
import json
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import re
from typing import Dict, List, Any, Optional, Union, cast, Literal

class DocumentQA:
    """Question answering system for documents using vector search and LLM"""
    
    def __init__(self, mongo_storage, vector_store, api_key=None, endpoint=None, deployment_name=None):
        """Initialize the QA system with storage and LLM components"""
        self.mongo_storage = mongo_storage
        self.vector_store = vector_store
        
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
                         json_response: bool = False, json_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Answer a question using semantic search and LLM generation
        
        Args:
            question: The question to answer
            n_results: Number of relevant chunks to retrieve
            filters: Optional filters for the vector search
            json_response: Whether to request a JSON response from the LLM
            json_schema: Optional JSON schema to guide the LLM response format
            
        Returns:
            Dict containing answer text and source information
        """
        # Search for relevant chunks
        relevant_chunks = self.vector_store.search(question, n_results=n_results, filters=filters)
        
        if not relevant_chunks:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "sources": []
            }
        
        # Format context for the LLM
        context = self._format_context(relevant_chunks)
        
        # Generate answer with LLM
        answer, citations = self._generate_answer(question, context, relevant_chunks, 
                                                 json_response=json_response, 
                                                 json_schema=json_schema)
        
        # Format sources
        sources = self._format_sources(relevant_chunks, citations)
        
        return {
            "answer": answer,
            "sources": sources
        }
    
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
                         json_response: bool = False, 
                         json_schema: Optional[Dict[str, Any]] = None) -> tuple[Union[str, Dict[str, Any]], List[int]]:
        """
        Generate an answer using the LLM
        
        Args:
            question: User question
            context: Formatted context from document chunks
            chunks: Document chunks for citation extraction
            json_response: Whether to request a structured JSON response
            json_schema: Optional schema for the JSON response
            
        Returns:
            Tuple of (answer, citations) where answer is either a string or a JSON object
        """
        # Prepare system message with instructions
        if json_response:
            system_message = """You are a helpful assistant that provides accurate information based on the provided document context. 
            When answering the question:
            1. Use only information from the provided context.
            2. If the context doesn't contain relevant information, say that you don't have enough information to answer.
            3. Your response must be valid JSON with the following structure:
               {
                 "answer": "Your detailed answer here",
                 "citations": [1, 2, ...] <- Document numbers from the context that support your answer
               }
            4. Provide comprehensive answers that directly address the question.
            5. When appropriate, include multiple citations to support your answer.
            6. Ensure that the citations are valid and that the document numbers are correct.
            """
            
            if json_schema:
                schema_str = json.dumps(json_schema, indent=2)
                system_message += f"\nYour response must conform to this JSON schema:\n{schema_str}"
        else:
            system_message = """You are a helpful assistant that provides accurate information based on the provided document context. 
            When answering the question:
            1. Use only information from the provided context.
            2. If the context doesn't contain relevant information, say that you don't have enough information to answer.
            3. Include citations in your answer using the format [Document X] where X is the document number from the context.
            4. Provide comprehensive answers that directly address the question.
            5. When appropriate, include multiple citations to support your answer.
            6. Ensure that the citations are valid and that the document numbers are correct."""
        
        # Prepare user message with question and context
        user_message = f"""Question: {question}

Context:
{context}

Please provide a detailed answer {"in JSON format " if json_response else ""}with citations to the relevant documents."""

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
    
    def _format_sources(self, chunks, citations):
        """Format source information from chunks and citations"""
        sources = []
        cited_docs = set()
        
        # First add cited documents
        for citation in citations:
            if 1 <= citation <= len(chunks):
                chunk = chunks[citation-1]
                doc_id = chunk["metadata"].get("document_id")
                
                if doc_id and doc_id not in cited_docs:
                    cited_docs.add(doc_id)
                    sources.append({
                        "document_id": doc_id,
                        "source": chunk["metadata"].get("source", "Unknown"),
                        "type": chunk["metadata"].get("type", "Unknown"),
                        "relevance": "cited"
                    })
        
        # Then add other relevant but uncited documents
        for i, chunk in enumerate(chunks):
            doc_id = chunk["metadata"].get("document_id")
            if doc_id and doc_id not in cited_docs:
                cited_docs.add(doc_id)
                sources.append({
                    "document_id": doc_id,
                    "source": chunk["metadata"].get("source", "Unknown"),
                    "type": chunk["metadata"].get("type", "Unknown"),
                    "relevance": "relevant"
                })
        
        return sources
    
    def get_document_by_id(self, document_id):
        """Get a full document by ID"""
        doc = self.mongo_storage.get_document(document_id)
        if doc:
            # Fetch all chunks
            chunks = self.mongo_storage.get_chunks_by_document(document_id)
            doc["chunks"] = chunks
            return doc
        return None