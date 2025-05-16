"""
Document loader module for handling different types of input documents.
"""
import os
import tempfile
from typing import List, Union
from langchain_community.document_loaders import UnstructuredURLLoader
from .ocr_processor import OCRProcessor

class DocumentLoader:
    def __init__(self):
        """Initialize the document loader with OCR processor."""
        self.ocr_processor = OCRProcessor()
        
    def process_urls(self, urls: List[str]) -> List[str]:
        """
        Process a list of URLs and extract their content.
        
        Args:
            urls: List of URLs to process
            
        Returns:
            List[str]: Extracted content from the URLs
        """
        loader = UnstructuredURLLoader(urls=urls)
        documents = loader.load()
        return [doc.page_content for doc in documents]
        
    def process_file(self, file) -> str:
        """
        Process an uploaded file and extract its content.
        
        Args:
            file: File object from Streamlit's file_uploader
            
        Returns:
            str: Extracted content from the file
        """
        # Create a temporary file to save the uploaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp_file:
            tmp_file.write(file.getvalue())
            tmp_file_path = tmp_file.name
            
        try:
            # Process the document using OCR
            content = self.ocr_processor.process_document(tmp_file_path)
            return content
        finally:
            # Clean up the temporary file
            os.unlink(tmp_file_path)
            
    def process_input(self, input_data: Union[List[str], List[tempfile.SpooledTemporaryFile]]) -> List[str]:
        """
        Process either URLs or files and return extracted content.
        
        Args:
            input_data: Either a list of URLs or a list of file objects
            
        Returns:
            List[str]: Extracted content from all inputs
        """
        if not input_data:
            return []
            
        # Check if input is URLs (strings) or files
        if isinstance(input_data[0], str):
            return self.process_urls(input_data)
        else:
            return [self.process_file(file) for file in input_data] 