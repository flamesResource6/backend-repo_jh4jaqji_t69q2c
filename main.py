import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from database import db, create_document, get_documents
from schemas import TypingResult

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Typing Test Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# API models
class SaveResultRequest(TypingResult):
    user_id: Optional[str] = None

class SaveResultResponse(BaseModel):
    id: str
    status: str

class ResultRecord(BaseModel):
    wpm: float
    accuracy: float
    mistakes: int
    duration: int
    created_at: datetime

@app.post("/api/results", response_model=SaveResultResponse)
def save_result(payload: SaveResultRequest):
    """Save a typing test result to the database."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    data = payload.model_dump()
    # Add server timestamp
    data["created_at"] = datetime.now(timezone.utc)
    # collection name from schema class: lowercased class name
    collection = "typingresult"
    try:
        inserted_id = create_document(collection, data)
        return {"id": inserted_id, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results", response_model=List[ResultRecord])
def list_results(limit: int = 50):
    """Fetch recent typing test results (for graph/history)."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        docs = get_documents("typingresult", {}, limit)
        # Normalize fields
        results: List[ResultRecord] = []
        for d in docs:
            results.append(ResultRecord(
                wpm=float(d.get("wpm", 0)),
                accuracy=float(d.get("accuracy", 0)),
                mistakes=int(d.get("mistakes", 0)),
                duration=int(d.get("duration", 60)),
                created_at=d.get("created_at", datetime.now(timezone.utc))
            ))
        # Sort by time ascending for graph
        results.sort(key=lambda x: x.created_at)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
