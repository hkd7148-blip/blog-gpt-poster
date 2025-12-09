import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import requests
from typing import Dict

app = FastAPI(title="Блог-пост генератор")

# Ключи берём из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")
currentsapi_key = os.getenv("CURRENTS_API_KEY")

if not openai.api_key:
    raise ValueError("OPENAI_API_KEY не установлен")
if not currentsapi_key:
    raise ValueError("CURRENTS_API_KEY не установлен")

class TopicRequest(BaseModel):
    topic: str

def get_recent_news(topic: str) -> str:
    url = "https://api.currentsapi.services/v1/search"
    params = {
        "keywords": topic,
        "language": "ru",
        "api_key": currentsapi_key
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        articles = data.get("news", [])[:5]
        if not articles:
            return "Свежих новостей по теме не найдено."
        titles = [a["title"] for a in articles]
        return "\n".join(titles)
    except:
        return "Ошибка при получении новостей."

def generate_post(topic: str) -> Dict[str, str]:
    news = get_recent_news(topic)

    # Генерируем заголовок
    title_response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Придумай яркий и кликабельный заголовок статьи на русском языке на тему «{topic}». Учти эти новости:\n{news}"}],
        max_tokens=100,
        temperature=0.7
    )
    title = title_response.choices[0].message.content.strip().strip('"')

    # Генерируем текст статьи
    post_response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""Напиши подробную статью на русском языке на тему «{topic}».
Используй эти свежие новости как основу:\n{news}

Требования:
- объём 1800–2500 символов
- структура: вступление → 3–4 подзаголовка → вывод
- короткие абзацы (3–5 строк)
- лёгкий живой язык
- используй Markdown-разметку заголовков (#, ##)
- НЕ используй символы _, *, `, [ ], ( ), кроме как в Markdown-заголовках"""}],
        max_tokens=2000,
        temperature=0.8
    )
    content = post_response.choices[0].message.content.strip()

    return {
        "title": title,
        "content": content
    }

@app.get("/")
async def root():
    return {"message": "Генератор постов работает! Отправь POST на /generate с темой."}

@app.post("/generate")
async def generate(request: TopicRequest):
    try:
        result = generate_post(request.topic)
        return {
            "topic": request.topic,
            "title": result["title"],
            "content": result["content"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
