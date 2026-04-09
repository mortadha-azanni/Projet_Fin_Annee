from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
import websockets   #type: ignore
import httpx
import os
import json
import re

app = FastAPI(
    title="Gateway Node",
    description="API Gateway for scraper and ranker microservices",
    version="0.1.0"
)

# Add CORS Middleware to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchQuery(BaseModel):
    query: str


class ChatQuery(BaseModel):
    message: str


class IntentQuery(BaseModel):
    message: str

SCRAPER_URL = os.getenv("SCRAPER_URL", "http://localhost:8001")
SCRAPER_WS_URL = SCRAPER_URL.replace("http://", "ws://").replace("https://", "wss://")
RANKER_URL = os.getenv("RANKER_URL", "http://localhost:8002")
RANKER_WS_URL = RANKER_URL.replace("http://", "ws://").replace("https://", "wss://")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

PRODUCT_INTENT_PATTERN = re.compile(
    r"(buy|purchase|recommend|suggest|looking for|need a|need an|find me|search|best|budget|price|laptop|pc|computer|phone|smartphone|tablet|headset|headphone|earbuds|keyboard|mouse|monitor|printer|camera|ssd|ram|gpu|iphone|samsung|xiaomi|macbook|lenovo|hp|asus|dell|portable|ordinateur|pc portable|t[ée]l[ée]phone|prix|produit|article)",
    re.IGNORECASE,
)


def heuristic_classify_intent(message: str) -> Dict[str, Any]:
    """Fallback intent classifier when LLM is unavailable or fails."""
    if PRODUCT_INTENT_PATTERN.search(message):
        return {
            "intent": "product_search",
            "confidence": 0.72,
            "source": "heuristic",
            "reason": "Matched shopping/product keywords",
        }

    return {
        "intent": "normal_chat",
        "confidence": 0.68,
        "source": "heuristic",
        "reason": "No strong shopping keyword signal",
    }


def extract_json_object(text: str) -> Dict[str, Any] | None:
    """Extract first JSON object from model output safely."""
    if not text:
        return None

    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None

    return None


async def llm_classify_intent(message: str) -> Dict[str, Any] | None:
    """Use Gemini to classify user intent into normal_chat or product_search."""
    if not GEMINI_API_KEY:
        return None

    classifier_prompt = (
        "Classify the user message into one of two intents:\n"
        "- product_search: user wants product recommendations, comparisons, prices, specs, or shopping help\n"
        "- normal_chat: greetings, general conversation, non-shopping Q&A\n\n"
        "Return strict JSON only with this schema:\n"
        '{"intent":"product_search|normal_chat","confidence":0.0,"reason":"short reason"}\n\n'
        f"User message: {message}"
    )

    request_payload = {
        "contents": [{"parts": [{"text": classifier_prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "topP": 0.1,
            "maxOutputTokens": 120,
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent"
    params = {"key": GEMINI_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, params=params, json=request_payload)
            if response.status_code == 429:
                return None
            response.raise_for_status()
            data = response.json()

        raw = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        parsed = extract_json_object(raw)
        if not parsed:
            return None

        intent = parsed.get("intent", "").strip().lower()
        if intent not in {"product_search", "normal_chat"}:
            return None

        confidence = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))
        reason = str(parsed.get("reason", "LLM classification"))[:140]

        return {
            "intent": intent,
            "confidence": confidence,
            "source": "llm",
            "reason": reason,
        }
    except Exception:
        return None


@app.get("/")
async def root():
    return {
        "service": "gateway-node",
        "status": "running",
        "scraper_url": SCRAPER_URL,
        "ranker_url": RANKER_URL,
        "redis_host": REDIS_HOST
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/services/health")
async def check_services_health():
    """Check health of all downstream services"""
    health_status = {
        "gateway": "healthy",
        "scraper": "unknown",
        "ranker": "unknown"
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check scraper
        try:
            response = await client.get(f"{SCRAPER_URL}/health")
            health_status["scraper"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            health_status["scraper"] = f"error: {str(e)}"
        
        # Check ranker
        try:
            response = await client.get(f"{RANKER_URL}/health")
            health_status["ranker"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            health_status["ranker"] = f"error: {str(e)}"
    
    return health_status


@app.get("/scrape-and-rank")
async def ETL(url: str):
    """
    Complete workflow: scrape URL and rank results
    
    Args:
        url: URL to scrape
    
    Returns:
        Ranked results from the scraped data
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Scrape the URL
            scrape_response = await client.get(
                f"{SCRAPER_URL}/scrape",
                params={"url": url}
            )
            scrape_response.raise_for_status()
            scrape_data = scrape_response.json()
            
            # Step 2: Rank the scraped data
            if scrape_data.get("data"):
                rank_response = await client.post(
                    f"{RANKER_URL}/rank",
                    json=scrape_data["data"]
                )
                rank_response.raise_for_status()
                rank_data = rank_response.json()
                
                return {
                    "success": True,
                    "url": url,
                    "scraped_items": len(scrape_data.get("data", [])),
                    "ranked_results": rank_data.get("ranked_items", []),
                    "final_response": rank_data.get("final_response", "")
                }
            else:
                return {
                    "success": True,
                    "url": url,
                    "scraped_items": 0,
                    "ranked_results": [],
                    "final_response": "",
                    "message": "No data scraped from URL"
                }
                
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Service error: {str(e)}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@app.post("/scrape/launch")
async def launch_scraping():
    """Proxy scrape launch request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SCRAPER_URL}/scrape/launch")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/pause")
async def pause_scraping():
    """Proxy scrape pause request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SCRAPER_URL}/scrape/pause")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/resume")
async def resume_scraping():
    """Proxy scrape resume request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SCRAPER_URL}/scrape/resume")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/stop")
async def stop_scraping():
    """Proxy scrape stop request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SCRAPER_URL}/scrape/stop")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scrape/status")
async def proxy_scraping_status():
    """Proxy scrape status request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{SCRAPER_URL}/scrape/status")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scrape/db-count")
async def proxy_scraping_db_count():
    """Proxy scraper DB count request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{SCRAPER_URL}/scrape/db-count")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/websocket_progress")
async def proxy_websocket_progress(websocket: WebSocket):
    """Proxy websocket connection to scraper node for progress updates"""
    await websocket.accept()
    scraper_ws_uri = f"{SCRAPER_WS_URL}/websocket_progress"
    
    try:
        async with websockets.connect(scraper_ws_uri) as scraper_ws:
            while True:
                # Receive message from scraper node and send to frontend client
                message = await scraper_ws.recv()
                await websocket.send_text(message)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"state": "error", "message": f"Gateway Websocket Error: {str(e)}"})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.post("/search")
async def search(query_data: SearchQuery):
    """Proxy search request to ranker node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{RANKER_URL}/search",
                json={"query": query_data.query}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Ranker service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/intent/classify")
async def classify_intent(query_data: IntentQuery):
    """Classify whether a user message is product search or regular chat."""
    user_message = (query_data.message or "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    llm_result = await llm_classify_intent(user_message)
    if llm_result:
        return llm_result

    return heuristic_classify_intent(user_message)


@app.post("/chat")
async def general_chat(query_data: ChatQuery):
    """General conversational endpoint for non-product chat."""
    user_message = (query_data.message or "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Missing GEMINI_API_KEY/API_KEY for LLM chat")

    prompt = (
        "You are a helpful shopping assistant chatbot. "
        "For normal conversation, respond naturally like a regular LLM. "
        "Keep responses concise, friendly, and practical."
    )

    request_payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{prompt}\n\nUser: {user_message}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.9,
            "maxOutputTokens": 512,
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent"
    params = {"key": GEMINI_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            data = None
            for attempt in range(2):
                response = await client.post(url, params=params, json=request_payload)

                if response.status_code in (429, 503) and attempt == 0:
                    # One quick retry for temporary provider-side throttling/outage.
                    continue

                if response.status_code == 429:
                    raise HTTPException(status_code=503, detail="LLM is currently rate-limited. Please retry shortly.")

                if response.status_code == 503:
                    raise HTTPException(status_code=503, detail="LLM service is temporarily unavailable. Please retry shortly.")

                if response.status_code >= 500:
                    raise HTTPException(status_code=503, detail="LLM provider is temporarily unavailable. Please retry shortly.")

                if response.status_code >= 400:
                    raise HTTPException(status_code=502, detail="LLM request was rejected by the provider.")

                data = response.json()
                break

            if data is None:
                raise HTTPException(status_code=503, detail="LLM service is temporarily unavailable. Please retry shortly.")

        generated_text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        if not generated_text:
            generated_text = "I couldn't generate a response right now. Please try again."

        return {"response": generated_text}
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Could not reach LLM service. Please retry shortly.")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Unexpected LLM service error.")
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Chat failed: {error}")

@app.websocket("/ws/status/{task_id}")
async def status_websocket(websocket: WebSocket, task_id: str):
    """Proxy websocket connection to ranker node"""
    await websocket.accept()
    ranker_ws_uri = f"{RANKER_WS_URL}/ws/status/{task_id}"
    
    try:
        async with websockets.connect(ranker_ws_uri) as ranker_ws:
            while True:
                # Receive message from ranker node and send to frontend client
                message = await ranker_ws.recv()
                await websocket.send_text(message)
                
                # Check for completion states
                try:
                    data = json.loads(message)
                    if data.get("state") in ["SUCCESS", "FAILURE"]:
                        break
                except:
                    pass
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"state": "FAILURE", "status": "Gateway Error", "error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
