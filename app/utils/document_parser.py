import os
import PyPDF2
import pandas as pd
import docx2txt
import json
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, TypedDict, NotRequired, Callable

# Define more flexible types for documents
class DocumentMetadata(TypedDict, total=False):
    """Type for document metadata"""
    source: str
    type: str
    pages: int
    title: str | None
    sheets: list[str]
    rows: int
    columns: list[str]

class ParsedDocument(TypedDict, total=False):
    """Type for parsed document results"""
    content: str
    metadata: dict[str, Any]  # More flexible to avoid cast issues
    structured_data: Any

class DocumentParser:
    """Parse various document types and extract text content"""
    
    def parse_file(self, file_path: str) -> ParsedDocument | None:
        """Parse a file based on its extension"""
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()
        
        try:
            if extension == '.pdf':
                return self.parse_pdf(file_path)
            elif extension in ['.docx', '.doc']:
                return self.parse_docx(file_path)
            elif extension in ['.xlsx', '.xls', '.csv']:
                return self.parse_spreadsheet(file_path)
            elif extension == '.txt':
                return self.parse_text(file_path)
            elif extension == '.json':
                return self.parse_json(file_path)
            elif extension in ['.html', '.htm']:
                return self.parse_html(file_path)
            else:
                print(f"Unsupported file format: {extension}")
                return None
        except Exception as e:
            print(f"Error parsing {file_path}: {str(e)}")
            return None
    
    def parse_pdf(self, file_path: str) -> ParsedDocument:
        """Extract text from PDF files"""
        text = ""
        metadata_dict: dict[str, Any] = {}
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract metadata if available
            if pdf_reader.metadata:
                metadata_dict = {k: v for k, v in pdf_reader.metadata.items() if v}
            
            # Extract text from each page
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {i+1} ---\n{page_text}"
        
        result: ParsedDocument = {
            "content": text,
            "metadata": {
                "source": file_path,
                "type": "pdf",
                "pages": len(pdf_reader.pages),
                **metadata_dict
            }
        }
        
        return result
    
    def parse_docx(self, file_path: str) -> ParsedDocument:
        """Extract text from Word documents"""
        # Use getattr to work around linter issues
        process_func = getattr(docx2txt, 'process')
        text = process_func(file_path)
        
        result: ParsedDocument = {
            "content": text,
            "metadata": {
                "source": file_path,
                "type": "docx"
            }
        }
        
        return result
    
    def parse_text(self, file_path: str) -> ParsedDocument:
        """Extract text from plain text files"""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            text = file.read()
        
        result: ParsedDocument = {
            "content": text,
            "metadata": {
                "source": file_path,
                "type": "text"
            }
        }
        
        return result
    
    def parse_json(self, file_path: str) -> ParsedDocument:
        """Extract data from JSON files"""
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        # Convert JSON to string representation for text storage
        content = json.dumps(data, indent=2)
        
        result: ParsedDocument = {
            "content": content,
            "structured_data": data,
            "metadata": {
                "source": file_path,
                "type": "json"
            }
        }
        
        return result
    
    def parse_html(self, file_path: str) -> ParsedDocument:
        """Extract text from HTML files"""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            html_content = file.read()
        
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.extract()
        
        # Get text
        text = soup.get_text(separator='\n')
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        title = soup.title.string if soup.title else None
        
        result: ParsedDocument = {
            "content": text,
            "metadata": {
                "source": file_path,
                "type": "html",
                "title": title
            }
        }
        
        return result
    
    def parse_spreadsheet(self, file_path: str) -> ParsedDocument:
        """Extract data from Excel/CSV files"""
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()
        
        if extension in ['.xlsx', '.xls']:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            sheets: Dict[str, pd.DataFrame] = {}
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheets[sheet_name] = df
            
            # Generate text representation
            text_content = ""
            for sheet_name, df in sheets.items():
                text_content += f"\n--- Sheet: {sheet_name} ---\n"
                text_content += df.to_string(index=False) + "\n"
            
            result: ParsedDocument = {
                "content": text_content,
                "structured_data": {sheet: df.to_dict('records') for sheet, df in sheets.items()},
                "metadata": {
                    "source": file_path,
                    "type": "excel",
                    "sheets": list(sheets.keys())
                }
            }
            
            return result
        
        elif extension == '.csv':
            df = pd.read_csv(file_path)
            
            result: ParsedDocument = {
                "content": df.to_string(index=False),
                "structured_data": df.to_dict('records'),
                "metadata": {
                    "source": file_path,
                    "type": "csv",
                    "rows": len(df),
                    "columns": list(df.columns)
                }
            }
            
            return result
            
        # This branch won't be reached due to the condition checks in parse_file
        # but it's needed to satisfy the type checker
        empty_result: ParsedDocument = {
            "content": "",
            "metadata": {"source": file_path, "type": "unknown"}
        }
        return empty_result