from fastapi import FastAPI, HTTPException, Response
from dotenv import load_dotenv
from pathlib import Path
import logging

from models import NewsRequest
from news_scrapper import NewsScrapper
from reddit_scrapper import scrape_reddit_topics
from summary_generator import generate_broadcast_news  
from elevenlabs_tts import text_to_audio_elevenlabs    

app = FastAPI()
load_dotenv()
logging.basicConfig(level=logging.INFO)

@app.post("/generate-news-audio")
async def generate_news_audio(request: NewsRequest):
    try:
        if not request.topics:
            raise HTTPException(status_code=400, detail="No topics provided.")

        logging.info(f"Generating summary for topics: {request.topics}")
        results = {}

        if request.source_type in ["news", "both"]:
            news_scrapper = NewsScrapper()
            results["news"] = await news_scrapper.scrape_news(request.topics)

        if request.source_type in ["reddit", "both"]:
            results["reddit"] = await scrape_reddit_topics(request.topics)

        news_data = results.get("news", {})
        reddit_data = results.get("reddit", {})

        news_summary = generate_broadcast_news(
            news_data=news_data,
            reddit_data=reddit_data,
            topics=request.topics
        )

        audio_path = text_to_audio_elevenlabs(
            text=news_summary,
            voice_id="en-US-AriaNeural",
            model_id="",
            output_format="mp3",
            output_dir="audio"
        )

        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
                return Response(
                    content=audio_bytes,
                    media_type="audio/mpeg",
                    headers={"Content-Disposition": "attachment; filename=summary.mp3"}
                )

        raise HTTPException(status_code=500, detail="Failed to generate audio.")

    except Exception as e:
        logging.exception("Error generating news audio")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
