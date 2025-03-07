from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.message import ChatMessage
from typing import List, Dict, Literal
from app.redis.users import get_user_conversation
from app.redis.redis import redis_client
from app.services.chatbot import ChatbotService

message_router = APIRouter()

chatbot_service = ChatbotService()

@message_router.post(
    '/messages', 
    response_model=ChatMessage, 
    status_code=status.HTTP_201_CREATED
)
async def process_message(message: ChatMessage):
    """
    Recibe un mensaje del chatbot, lo procesa (por ejemplo, analizando el sentimiento) 
    y lo almacena antes de enviarlo al LLM para una respuesta final.
    """
    try:
        # Almacenar el mensaje en Redis
        redis_key = f"chat:{message.user_id}"
        redis_client.rpush(redis_key, message.text)  # Agrega el mensaje a la lista de Redis

        # Se carga toda la conversacion anterior y el mensaje actual
        conversation_history: List[Dict[Literal["role", "content"], str]] = get_user_conversation(message.user_id)

        # Obtener la respuesta del chatbot
        chatbot_response = chatbot_service.get_chat_response(conversation_history)

        # Verificar si la respuesta es None
        if chatbot_response is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo generar una respuesta."
            )

        redis_client.rpush(redis_key, chatbot_response)

        # Devolver la respuesta con el resultado del análisis
        return ChatMessage(user_id=message.user_id, text=chatbot_response)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


