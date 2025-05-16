"""
Parallel executor module for handling concurrent processing of multiple AI models.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
import os
from .ai_processors import AIProcessor

class ParallelExecutor:
    def __init__(self):
        """Initialize the parallel executor with AI processor."""
        self.ai_processor = AIProcessor()
        self.max_workers = int(os.getenv('MAX_PARALLEL_THREADS', 3))
        
    async def process_query(self, query: str, context: str) -> Dict[str, Any]:
        """
        Process a query through multiple AI models in parallel.
        
        Args:
            query: User's question
            context: Context from processed documents
            
        Returns:
            Dict containing responses from all models
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            loop = asyncio.get_event_loop()
            responses = await self.ai_processor.process_parallel(query, context)
            
            return {
                "responses": responses,
                "metadata": {
                    "models_used": list(responses.keys()),
                    "query": query,
                    "context_length": len(context)
                }
            }
            
    def format_responses(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the responses for display.
        
        Args:
            result: Raw responses from AI models
            
        Returns:
            Dict containing formatted responses
        """
        responses = result["responses"]
        
        formatted_response = {
            "answer": "",
            "sources": [],
            "model_responses": {}
        }
        
        # Format responses from different models
        for model, response in responses.items():
            formatted_response["model_responses"][model] = {
                "response": response["response"]
            }
            
        # Use GPT-4o response as primary if available
        if "gpt-4o" in responses:
            formatted_response["answer"] = responses["gpt-4o"]["response"]
        elif responses:
            # Use first available response
            formatted_response["answer"] = next(iter(responses.values()))["response"]
            
        return formatted_response

    def format_final_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the final response with all model outputs.
        
        Args:
            result: Raw responses from AI models
            
        Returns:
            Dict containing formatted responses from all models
        """
        responses = result["responses"]

        # Build results list
        results_list = []
        for model, response in responses.items():
            results_list.append({
                "model": model,
                "answer": response["response"]
            })

        # Extract sources from responses if available
        sources = []
        for response in responses.values():
            if "sources" in response:
                sources.extend(response["sources"])

        return {
            "results": results_list,
            "sources": list(set(sources))  # Remove duplicates
        } 