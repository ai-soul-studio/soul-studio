import os
import requests
from dotenv import load_dotenv
from . import config
import logging

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')


def search_web(query: str, num_results: int = 3):
    """Perform a web search using Brave Search API"""
    if not BRAVE_API_KEY:
        logger.error("BRAVE_API_KEY not found in environment variables")
        return []
    
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    
    params = {
        "q": query,
        "count": num_results
    }
    
    try:
        logger.info(f"Performing web search for query: {query}")
        response = requests.get(
            config.BRAVE_SEARCH_API_URL,
            headers=headers,
            params=params,
            timeout=10  # Add timeout for better error handling
        )
        response.raise_for_status()
        
        results = []
        search_data = response.json()
        web_results = search_data.get('web', {}).get('results', [])
        
        for item in web_results[:num_results]:
            results.append({
                "title": item.get('title', 'No title'),
                "url": item.get('url', ''),
                "description": item.get('description', 'No description')
            })
        
        logger.info(f"Found {len(results)} search results")
        return results
    
    except requests.exceptions.Timeout:
        logger.error(f"Web search timeout for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Web search request error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected web search error: {e}")
        return []


def format_search_results(results):
    """Format search results for agent use"""
    if not results:
        return "No results found"
        
    formatted = []
    for i, result in enumerate(results, 1):
        formatted.append(
            f"{i}. [{result['title']}]({result['url']})\n"
            f"   {result.get('description', 'No description')}"
        )
    return "\n\n".join(formatted)
