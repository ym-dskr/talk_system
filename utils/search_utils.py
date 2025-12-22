from tavily import TavilyClient
from config import TAVILY_API_KEY
import asyncio

class TavilySearcher:
    def __init__(self):
        self.client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

    async def search(self, query: str):
        if not self.client:
            return "Search API key is not configured."
        
        try:
            # Running synchronous Tavily client in a thread pool to avoid blocking asyncio
            print(f"[SEARCH] Querying Tavily: {query}")
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.client.search(query=query, search_depth="basic")
            )
            
            results = response.get('results', [])
            if not results:
                return "No results found."
            
            formatted_results = []
            for res in results[:3]:  # Limit to top 3 results for brevity
                formatted_results.append(f"Title: {res['title']}\nContent: {res['content']}\nURL: {res['url']}")
            
            return "\n\n".join(formatted_results)
        except Exception as e:
            print(f"[SEARCH] Error during search: {e}")
            return f"An error occurred during search: {str(e)}"
