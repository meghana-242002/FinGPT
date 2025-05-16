import os
from typing import Dict, Any
from openai import AsyncOpenAI
import aiohttp
from dotenv import load_dotenv
import logging
import asyncio

# Load environment variables
load_dotenv()

class AIProcessor:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
        
        if not self.openai_api_key:
            logging.warning("OpenAI API key not found in environment variables")
        if not self.perplexity_api_key:
            logging.warning("Perplexity API key not found in environment variables")
        
    async def get_gpt_response(self, query: str, context: str) -> Dict[str, Any]:
        try:
            client = AsyncOpenAI(api_key=self.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant analyzing financial documents and news articles. Provide detailed, accurate responses and cite specific parts of the context when possible."},
                    {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
                ],
                temperature=float(os.getenv('TEMPERATURE', 0.7)),
                max_tokens=500
            )
            return {
                "model": "gpt-4o",
                "response": response.choices[0].message.content,
                "confidence": response.choices[0].finish_reason == "stop"
            }
        except Exception as e:
            logging.error(f"Error in GPT processing: {str(e)}")
            return {"model": "gpt-3.5-turbo", "error": str(e)}
            
    async def get_perplexity_response(self, query: str, context: str, model: str) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant analyzing financial documents and news articles. Provide detailed, accurate responses and cite specific parts of the context when possible."},
                        {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
                    ]
                }
                async with session.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Perplexity API error: {error_text}")
                    result = await response.json()
                    model_name = model
                    return {
                        "model": model_name,
                        "response": result['choices'][0]['message']['content'],
                        "confidence": True
                    }
        except Exception as e:
            model_name = model
            logging.error(f"Error in Perplexity {model} processing: {str(e)}")
            return {"model": model_name, "error": str(e)}
            
    async def process_parallel(self, query: str, context: str) -> Dict[str, Any]:
        tasks = []
        if self.openai_api_key:
            tasks.append(self.get_gpt_response(query, context))
        if self.perplexity_api_key:
            tasks.extend([
                self.get_perplexity_response(query, context, "sonar-pro"),
                self.get_perplexity_response(query, context, "sonar")
            ])
        if not tasks:
            logging.error("No API keys configured - cannot process query")
            return {}
        results = await asyncio.gather(*tasks, return_exceptions=True)
        responses = {}
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Error in parallel processing: {str(result)}")
                continue
            if isinstance(result, dict) and "error" not in result:
                responses[result["model"]] = {
                    "response": result["response"],
                    "confidence": result["confidence"]
                }
        if not responses:
            responses["error"] = {
                "response": "Unable to process query. Please check API keys and try again.",
                "confidence": False
            }
        return responses 

    def format_final_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        responses = result["responses"]
        results_list = []
        for model, response in responses.items():
            answer = response["response"].strip()
            results_list.append({
                "model": model,
                "answer": answer
            })
        return {
            "results": results_list,
            "sources": []
        }