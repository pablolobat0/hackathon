from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from typing import List, Dict, Optional, Literal

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de la API 
API_KEY = os.getenv("PERPLEXITY_API_KEY")
API_URL ="https://api.perplexity.ai" 

class ChatbotService:
    def __init__(self):
        self.client = OpenAI(api_key=API_KEY, base_url=API_URL)

    def get_chat_response(self, messages: List[Dict[Literal["role", "content"], str]]) -> Optional[str]:
        """
        Obtiene una respuesta basada en los mensajes de la conversacion enviada.

        :param messages: Lista de mensajes en formato de diccionario con claves "role" y "content".
        :return: Respuesta generada o None si hay un error.
        """
        # Agregar un prompt inicial de sistema para definir el comportamiento del chatbot
        system_prompt = {
            "role": "system",
            "content": (
                "Eres un terapeuta virtual amigable y empático especializado en brindar apoyo emocional y orientación psicológica. "
                "Tu objetivo es escuchar activamente a los usuarios, ofrecer respuestas empáticas y ayudarles a reflexionar sobre sus emociones y situaciones. "
                "Habla de manera cálida y profesional, y evita dar diagnósticos médicos o tratamientos. "
                "Ofrece herramientas de afrontamiento, preguntas reflexivas y sugerencias generales para mejorar el bienestar emocional. "
                "Recuerda: tu rol es escuchar y guiar, no juzgar."
            )
        }

        return self.get_chatbot_response(system_prompt, messages)

    def get_personality_scores(self, messages: List[Dict[Literal["role", "content"], str]]) -> Optional[str]:
        """
        Obtiene las puntuaciones de personalidad del usuario según el modelo Big Five.

        :param messages: Lista de mensajes en formato de diccionario con claves "role" y "content".
        :return: JSON con las puntuaciones de personalidad o None si hay un error.
        """
    # Prompt de sistema para analizar la personalidad
        system_prompt = {
            "role": "system",
            "content": (
                "Eres un psicólogo virtual especializado en el modelo de personalidad Big Five. "
                "Analiza los mensajes del usuario y devuelve un JSON con las puntuaciones de los cinco rasgos de personalidad: "
                "Apertura (Openness), Responsabilidad (Conscientiousness), Extraversión (Extraversion), Amabilidad (Agreeableness) y Neuroticismo (Neuroticism). "
                "Las puntuaciones deben estar en una escala del 1 al 5, donde 1 es el mínimo y 5 es el máximo. "
                "Quiero que solo respondas con el JSON. El formato del JSON debe ser: "
                '{"openness": puntuacion, "conscientiousness": puntuacion, "extraversion": puntuacion, "agreeableness": puntuacion, "neuroticism": puntuacion}.'
            )
        }

        # Obtener la respuesta del chatbot
        response = self.get_chatbot_response(system_prompt, messages)
        
        if not response:
            raise ValueError("Error del mensaje")

        # Intentar parsear la respuesta como JSON
        try:
            personality_scores = json.loads(response)
            return personality_scores
        except json.JSONDecodeError:
            return None

    def get_emotional_advice(self, messages: List[Dict[Literal["role", "content"], str]]) -> Optional[str]:
        """
        Proporciona consejos personalizados según el tipo emocional del usuario.

        :param messages: Lista de mensajes en formato de diccionario con claves "role" y "content".
        :return: Consejos personalizados o None si hay un error.
        """
        # Prompt de sistema para dar consejos emocionales
        system_prompt = {
            "role": "system",
            "content": (
                "Eres un terapeuta virtual especializado en bienestar emocional. "
                "Analiza los mensajes del usuario y proporciona consejos personalizados para mejorar su bienestar emocional. "
                "Los consejos deben basarse en el tipo emocional del usuario (por ejemplo, si muestra ansiedad, estrés, tristeza, etc.). "
                "Sé empático, profesional y ofrece herramientas prácticas para afrontar las emociones. "
                "Evita dar diagnósticos médicos o tratamientos específicos."
                "Retorna 4 oraciones separadas por salto de línea con los consejos que sean estilo Consejo: descripción"
            )
        }

        # Obtener la respuesta del chatbot
        response = self.get_chatbot_response(system_prompt, messages)

        return response

    def get_chatbot_response(self, system_prompt: dict, messages: List[Dict[Literal["role", "content"], str]]) -> Optional[str]:
        # Combinar el prompt inicial con los mensajes del usuario
        full_messages = [system_prompt] + messages
        try:
            # Llamada a la API 
            response = self.client.chat.completions.create(
                model="r1-1776",
                messages=full_messages #type: ignore
            )
             # Obtener el contenido de la respuesta
            full_response = response.choices[0].message.content

            # Procesar la respuesta para eliminar el razonamiento
            if full_response and "</think>" in full_response:
                # Extraer solo la parte después de </think>
                final_response = full_response.split("</think>")[-1].strip()
                return final_response
            else:
                # Si no hay etiqueta </think>, devolver la respuesta completa
                return full_response
        except Exception as e:
            print(f"Error en la llamada a la API: {e}")
            return None
