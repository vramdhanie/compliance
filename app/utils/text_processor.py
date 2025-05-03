import re
import uuid

class TextProcessor:
    """Process and chunk text for efficient storage and retrieval"""
    
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_document(self, document):
        """Process a document and split into chunks"""
        doc_content = document["content"]
        doc_metadata = document["metadata"]
        
        # Extract concepts and keywords
        concepts = self.extract_concepts(doc_content)
        
        # Split text into chunks
        chunks = self.split_text(doc_content)
        
        processed_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            
            # Create chunk document
            chunk_doc = {
                "chunk_id": chunk_id,
                "document_id": doc_metadata.get("source"),
                "content": chunk_text,
                "chunk_index": i,
                "concepts": self.extract_concepts(chunk_text),
                "metadata": {
                    **doc_metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            }
            
            processed_chunks.append(chunk_doc)
        
        # Create document summary
        document_summary = {
            "document_id": doc_metadata.get("source"),
            "title": self._extract_title(doc_content) or doc_metadata.get("source"),
            "concepts": concepts,
            "summary": self._generate_summary(doc_content),
            "metadata": doc_metadata,
            "chunks": [chunk["chunk_id"] for chunk in processed_chunks]
        }
        
        return document_summary, processed_chunks
    
    def split_text(self, text):
        """Split text into overlapping chunks"""
        if not text:
            return []
            
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk of appropriate size
            end = start + self.chunk_size
            
            # If we're not at the end, try to break at a paragraph or sentence
            if end < len(text):
                # Try to find a paragraph break
                paragraph_break = text.rfind('\n\n', start, end)
                
                if paragraph_break != -1 and paragraph_break > start + self.chunk_size / 2:
                    end = paragraph_break + 2
                else:
                    # Try to find a sentence break
                    sentence_break = text.rfind('. ', start, end)
                    if sentence_break != -1 and sentence_break > start + self.chunk_size / 2:
                        end = sentence_break + 2
            
            # Get the chunk and add it to our list
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move the start pointer, accounting for overlap
            start = end - self.chunk_overlap
            
            # Make sure we're making progress
            if start <= 0:
                start = end
        
        return chunks
    
    def extract_concepts(self, text):
        """Extract key concepts from text"""
        if not text:
            return []
            
        # Simple implementation - extract capitalized phrases and keywords
        # In a production system, you might use NER or topic modeling
        concepts = set()
        
        # Find capitalized phrases (potential named entities)
        cap_phrases = re.findall(r'\b[A-Z][A-Za-z]+([ \-][A-Z][A-Za-z]+)*', text)
        for phrase in cap_phrases:
            if len(phrase) > 3:  # Avoid short acronyms
                concepts.add(phrase)
        
        # Find potential key terms using common patterns
        key_patterns = [
            r'\b(?:defined as|refers to|means) ([^.;:!?]+)',  # Definition patterns
            r'"([^"]{5,})"',  # Quoted important terms
            r'\b(?:important|crucial|key|main|primary|essential) (?:concept|aspect|feature|element|component|part)s? (?:is|are|includes?) ([^.;:!?]+)'
        ]
        
        for pattern in key_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 10:  # Avoid very short matches
                    concepts.add(match.strip())
        
        return list(concepts)[:20]  # Limit to top 20 concepts
    
    def _extract_title(self, text):
        """Extract a potential title from the text"""
        if not text:
            return None
            
        # Try to find a title at the beginning of the document
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            # If first line looks like a title (not too long, no punctuation at end)
            if 3 < len(first_line) < 100 and not first_line[-1] in '.,:;?!':
                return first_line
                
        return None
    
    def _generate_summary(self, text):
        """Generate a simple summary by extracting key sentences"""
        if not text or len(text) < 100:
            return text
            
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Score sentences based on position and keywords
        scores = {}
        for i, sentence in enumerate(sentences):
            score = 0
            
            # Position score - early sentences get higher scores
            position_score = 1.0 - (i / len(sentences))
            score += position_score * 0.3
            
            # Length score - prefer medium-length sentences
            length = len(sentence)
            if 20 < length < 200:
                score += 0.2
            
            # Keyword score
            indicators = ["important", "significant", "key", "main", "primary", 
                        "crucial", "essential", "fundamental", "core", "critical"]
            for word in indicators:
                if word in sentence.lower():
                    score += 0.5
                    
            scores[sentence] = score
        
        # Get top sentences
        top_sentences = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Take top 3 sentences or 10% of sentences, whichever is greater
        num_summary_sentences = max(3, int(len(sentences) * 0.1))
        summary_sentences = [s[0] for s in top_sentences[:num_summary_sentences]]
        
        # Sort by original position
        summary_sentences = [s for s in sentences if s in summary_sentences]
        
        return " ".join(summary_sentences)