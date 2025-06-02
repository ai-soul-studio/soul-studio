import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')


def search_web(query: str, num_results: int = 3):
    """Perform a web search using Brave Search API"""
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    
    params = {
        "q": query,
        "count": num_results
    }
    
    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        
        results = []
        for item in response.json().get('web', {}).get('results', [])[:num_results]:
            results.append({
                "title": item.get('title'),
                "url": item.get('url'),
                "description": item.get('description')
            })
        return results
    
    except Exception as e:
        print(f"Web search error: {e}")
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
