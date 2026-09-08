"""Aggregates every route module into a single router mounted by main.py."""

from fastapi import APIRouter

from app.api.routes import auth, devices, health, media, playlists, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(media.router)
api_router.include_router(playlists.router)
api_router.include_router(devices.router)
api_router.include_router(users.router)
