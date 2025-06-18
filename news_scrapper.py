import asyncio
import os
from typing import Dict, List

from aiolimiter import AsyncLimiter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv


from utils import(
    generate_news_urls_to_scrape,
    scrape_with_brightdata,
    clean_html_to_text,
    extract_headlines,
    summarize_with_groq_news_script
)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
load_dotenv()

class NewsScrapper:
    _rate_limiter = AsyncLimiter(5,1)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def scrape_news(self,topics:List[str])->Dict[str,str]:
        """Scrape news from the provided topics"""
        results={}
        for topic in topics:
            async with self._rate_limiter:
                try:
                    urls=generate_news_urls_to_scrape([topic])
                    search_html=await scrape_with_brightdata(urls[topic])
                    cleaned_text=clean_html_to_text(search_html)
                    headlines=extract_headlines(cleaned_text)
                    summary=summarize_with_groq_news_script(headlines)
                    results[topic]=summary
                except Exception as e:
                    results[topic]=f"Error scraping news: {e}"
                await asyncio.sleep(1)
        return {"news_analysis": results}
