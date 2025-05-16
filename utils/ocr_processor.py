"""
Google Cloud Vision OCR processor for extracting text from images and PDFs.
"""
import os
from google.cloud import vision
from pdf2image import convert_from_path
from PIL import Image
import io
import logging

class OCRProcessor:
    def __init__(self):
        """Initialize the Google Cloud Vision client."""
        self.client = vision.ImageAnnotatorClient()
        
    def extract_text_from_image(self, image_path):
        """
        Extract text from an image using Google Cloud Vision API.
        
        Args:
            image_path: Path to the image file or bytes of the image
            
        Returns:
            str: Extracted text from the image
        """
        try:
            # If image_path is a string (file path)
            if isinstance(image_path, str):
                with open(image_path, 'rb') as image_file:
                    content = image_file.read()
            # If image_path is bytes
            else:
                content = image_path
                
            image = vision.Image(content=content)
            response = self.client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))
                        
            return response.full_text_annotation.text
            
        except Exception as e:
            logging.error(f"Error in OCR processing: {str(e)}")
            raise
            
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from a PDF file by converting it to images and processing each page.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            str: Extracted text from all pages
        """
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            extracted_text = []
            
            # Process each page
            for image in images:
                # Convert PIL Image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Extract text from the image
                page_text = self.extract_text_from_image(img_byte_arr)
                extracted_text.append(page_text)
                
            return "\n\n".join(extracted_text)
            
        except Exception as e:
            logging.error(f"Error in PDF processing: {str(e)}")
            raise
            
    def process_document(self, file_path):
        """
        Process a document file (PDF or image) and extract text.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            str: Extracted text from the document
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}") 