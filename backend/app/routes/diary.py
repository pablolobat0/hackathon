from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.db.crud.user import update_user_emotions
from app.models.diary import DiaryEntry
from app.db.utils import get_database
from app.db.crud.diary import (
    get_all_diary_entries_by_user_id,
    create_diary_entry,
    get_diary_entry_by_title,
    delete_diary_entry_by_title
)
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List, Dict, Literal
import json
import re

from app.services.chatbot import ChatbotService


diary_router = APIRouter()

chatbot_service = ChatbotService()

@diary_router.post(
    '/diary',
    response_model=DiaryEntry,
    status_code=status.HTTP_201_CREATED
)
async def create_entry(entry: DiaryEntry, db: AsyncIOMotorCollection = Depends(get_database)):
    """
    Recibe una entrada del diario, la analiza y la guarda.
    Se verifica que no exista ya una entrada con el mismo título.
    """
    try:
        # Verificar si ya existe una entrada con el mismo título
        existing_entry = await db.diary.find_one({"user_id": entry.user_id, "titulo": entry.titulo})
        if existing_entry:
            raise ValueError("Ya existe una entrada con el mismo título.")

        # Crear la entrada en la base de datos
        created_entry = await create_diary_entry(db.diary, entry)

        all_entries = await get_all_diary_entries_by_user_id(db.diary, entry.user_id)

        all_text = " ".join([entry["entrada"] for entry in all_entries])
        all_messages: List[Dict[Literal["role", "content"], str]] = [
            {"role": "user", "content": all_text}] 

        response = chatbot_service.get_personality_scores(all_messages)
        if not response:
            raise ValueError("Error en la respuesta del LLM: Respuesta vacía o inválida")
        # Si la respuesta es un diccionario, úsalo directamente
        if isinstance(response, dict):
            personality_scores = response
        # Si la respuesta es un string JSON, conviértelo a diccionario
        elif isinstance(response, str):
            # Expresión regular para extraer el JSON
            json_pattern = re.compile(r'\{.*?"openness":\s*\d+(\.\d+)?.*?"conscientiousness":\s*\d+(\.\d+)?.*?"extraversion":\s*\d+(\.\d+)?.*?"agreeableness":\s*\d+(\.\d+)?.*?"neuroticism":\s*\d+(\.\d+)?.*?\}')

            # Buscar el JSON en la respuesta del LLM
            match = json_pattern.search(response)
            if not match:
                raise ValueError("No se encontró un JSON válido en la respuesta del LLM")

            # Extraer el JSON
            json_content = match.group(0)

            # Parsear el JSON
            try:
                personality_scores = json.loads(json_content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Error al parsear el JSON: {e}")
        else:
            raise ValueError("Tipo de respuesta no válido del LLM")

        await update_user_emotions(db.users, entry.user_id, personality_scores)

        return created_entry
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@diary_router.get(
    '/diary',
    response_model=List[DiaryEntry],
    status_code=status.HTTP_200_OK
)
async def get_all_entries(user_id: str, db: AsyncIOMotorCollection = Depends(get_database)):
    """
    Devuelve todas las entradas del diario.
    """
    entries = await get_all_diary_entries_by_user_id(db.diary, user_id)
    return entries

@diary_router.get(
    '/diary/{titulo}',
    response_model=DiaryEntry,
    status_code=status.HTTP_200_OK
)
async def get_entry_by_title(titulo: str, db: AsyncIOMotorCollection = Depends(get_database)):
    """
    Devuelve una única entrada del diario según el título desde MongoDB.
    """
    entry = await get_diary_entry_by_title(db.diary, titulo)
    if entry:
        return entry
    raise HTTPException(
        status_code=404,
        detail="Entrada del diario no encontrada."
    )

@diary_router.delete(
    '/diary/{titulo}',
    status_code=status.HTTP_200_OK
)
async def delete_entry_by_title(titulo: str, db: AsyncIOMotorCollection = Depends(get_database)):
    """
    Elimina una entrada del diario según el título desde MongoDB.
    """
    deleted = await delete_diary_entry_by_title(db.diary, titulo)
    if deleted:
        return {"detail": f"Entrada '{titulo}' eliminada correctamente."}
    raise HTTPException(
        status_code=404,
        detail="Entrada del diario no encontrada."
    )
