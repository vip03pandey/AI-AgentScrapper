from urllib.parse import quote_plus
import os
import requests
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

def generate_valid_news_url(keyword:str)->str:
    """Generate a valid news url from a keyword
    Args:
        keyword (str): The keyword to generate the url from
    Returns:
        str: The generated url
    """
    q=quote_plus(keyword)
    return f"https://www.google.com/search?q={q}&tbs=sbd:1"

def scrape_with_brightdata(url:str)->str:
    """Scrape the content from a url using Brightdata"""
    headers={
        "Authorization": f"Bearer {os.getenv['BRIGHT_DATA_API']}",
        "Content-Type": "application/json"

    }
    payload={
        "url":url,
        "zone":os.getenv['WEB_UNLOCKER_ZONE'],
        "format":"raw"
    }

    try:
        response=requests.post("https://api.brightdata.com/request",headers=headers,json=payload)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as e:
        print(f"Error scraping with brightdata: {e}")
        return ""
def clean_html_to_text(html_content:str)->str:
    soup=BeautifulSoup(html_content,"html.parser")
    text=soup.get_text(separator="\n")
    return text.strip()

def extract_headlines(cleaned_text:str)->str:
    """"Extract the headlines from the cleaned text
    Args:
        cleaned_text (str): The cleaned text to extract the headlines from
    Returns:
        str: The extracted headlines
    """
    headlines=[]
    current_block=[]
    lines=[lines.strip() for lines in cleaned_text.split("\n") if lines.strip()]
    for line in lines:
        if line=="More":
            if current_block:
                headlines.append(current_block[0])
                current_block=[]
            else:
                current_block.append(line)

    if current_block:
        headlines.append(current_block[0])
    return "\n".join(headlines)


def summarize_with_groq_news_script(headlines:str)->str:
    """
    Summarize multiple news headlines into a TTS-friendly broadcast news script using Anthropic Claude model via LangChain.
    """
    system_prompt = """
    You are my personal news editor and scriptwriter for a news podcast. Your job is to turn raw headlines into a clean, professional, and TTS-friendly news script.

    The final output will be read aloud by a news anchor or text-to-speech engine. So:
    - Do not include any special characters, emojis, formatting symbols, or markdown.
    - Do not add any preamble or framing like "Here's your summary" or "Let me explain".
    - Write in full, clear, spoken-language paragraphs.
    - Keep the tone formal, professional, and broadcast-style — just like a real TV news script.
    - Focus on the most important headlines and turn them into short, informative news segments that sound natural when spoken.
    - Start right away with the actual script, using transitions between topics if needed.

    Remember: Your only output should be a clean script that is ready to be read out loud.
    """

    try:
        llm=ChatGroq(model_name="Gemma2-9b-It",temperature=0.5,max_tokens=1000)
        response=llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=headlines)
        ])
        return response.content
    except Exception as e:
        print(f"Error summarizing with groq: {e}")


def generate_news_urls_to_scrape(list_of_keywords):
    valid_urls_dict={}
    for keyword in list_of_keywords:
        valid_urls_dict[keyword]=generate_valid_news_url(keyword)
    return valid_urls_dict
    


    
    