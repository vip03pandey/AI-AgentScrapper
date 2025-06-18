from urllib.parse import quote_plus
import os
import requests
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from elevenlabs import ElevenLabs
import datetime
from dotenv import load_dotenv
load_dotenv()


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
    headers = {
    "Authorization": f"Bearer {os.getenv('BRIGHT_DATA_API')}",
    "Content-Type": "application/json"
    }
    payload = {
        "zone": os.getenv('WEB_UNLOCKER_ZONE'),
        "url": "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api",
        "format": "raw"
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


def summarize_with_groq_news_script(headlines: str) -> str:
    """
    Summarize multiple news headlines into a TTS-friendly broadcast news script using Groq model via LangChain.
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
        if len(headlines) > 4000:
            headlines = headlines[:4000] + "\n\n[Truncated due to input limit]"

        llm = ChatGroq(model_name="Gemma2-9b-It", temperature=0.5)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=headlines)
        ])
        return response.content

    except Exception as e:
        print(f"Error summarizing with groq: {e}")
        return "Error: Could not generate summary."


def generate_news_urls_to_scrape(list_of_keywords):
    valid_urls_dict={}
    for keyword in list_of_keywords:
        valid_urls_dict[keyword]=generate_valid_news_url(keyword)
    return valid_urls_dict
    

def generate_broadcast_news(news_data,reddit_data,topics)->str:
    system_prompt = """You are a news reporter. Create a concise 60-second news script from the provided topics.
    - Start directly with content
    - Keep it brief and focused
    - Use natural speech transitions
    - Maintain professional tone
    - No introductions or conclusions needed"""
    
    try:
        topic_blocks = []
        for topic in topics:
            news_content = news_data.get("news_analysis", {}).get(topic, "") if news_data else ""
            reddit_content = reddit_data.get("reddit_analysis", {}).get(topic, "") if reddit_data else ""
            
            # Limit content length
            if news_content:
                news_content = news_content[:200] + "..." if len(news_content) > 200 else news_content
            if reddit_content:
                reddit_content = reddit_content[:200] + "..." if len(reddit_content) > 200 else reddit_content
            
            context = []
            if news_content:
                context.append(f"News: {news_content}")
            if reddit_content:
                context.append(f"Reddit: {reddit_content}")
            if context:
                topic_blocks.append(f"{topic}: " + " | ".join(context))

        user_prompt = "Topics:\n" + "\n".join(topic_blocks)
        
        llm = ChatGroq(
            model_name="Gemma2-9b-It",
            temperature=0.5,
            max_tokens=500  # Reduced token limit
        )
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        return response.content
    except Exception as e:  
        print(f"Error generating broadcast news: {e}")
        return "Error generating news broadcast. Please try again with fewer topics or shorter content."


def text_to_audio_elevenlabs(
        text: str,
        voice_id: str = '21m00Tcm4TlvDq8ikWAM',  
        model_id: str = 'eleven_multilingual_v2',
        output_format: str = 'mp3_44100_128',
        output_dir: str = 'audio',
        api_key: str = None
) -> str:
    try:
        api_key = api_key or os.getenv('ELEVEN_LABS_API_KEY')
        if not api_key:
            raise ValueError("ElevenLabs API key not found")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            },
            "output_format": output_format
        }

        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        os.makedirs(output_dir, exist_ok=True)
        filename = f"tts_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp3"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return filepath

    except Exception as e:
        print(f"Error generating audio from text: {e}")
        return ""



    
    