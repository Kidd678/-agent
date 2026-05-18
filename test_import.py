import sys
sys.path.insert(0, '.')

print('step 1: fastapi')
from fastapi import FastAPI, APIRouter

print('step 2: models')
from app.models.request import ChatRequest
from app.models.response import ChatResponse

print('step 3: intent')
from app.services.intent.classifier import IntentClassifier

print('step 4: memory')
from app.services.memory.session_store import SessionStore

print('step 5: routing')
from app.services.routing.router import Router

print('step 6: routes')
from app.routes.chat import router as chat_router

print('step 7: main')
from app.main import app

print('all ok')
