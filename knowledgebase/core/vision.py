"""
Vision AI Integration für die Bildbeschreibung.
"""
import base64
import mimetypes
from pathlib import Path
from openai import OpenAI
from knowledgebase.config import get_openai_api_key, LLM_MODEL


def encode_image(image_path: Path) -> str:
    """Wandelt ein Bild in einen Base64-String um."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def get_image_description(image_path: Path) -> str:
    """
    Sendet ein Bild an GPT-4o Vision und erhält eine detaillierte Beschreibung.
    """
    client = OpenAI(api_key=get_openai_api_key())
    base64_image = encode_image(image_path)
    
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"
    
    # SVGs können von GPT-4o Vision nicht direkt verarbeitet werden (Raster nötig)
    if "svg" in mime_type:
        return "[Vektorgrafik (SVG) - keine automatische Beschreibung verfügbar]"

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Beschreibe dieses Bild aus einem Fachbuch detailliert. Erfasse Diagramme, Formeln, Tabelleninhalte oder Illustrationen, sodass sie textuell suchbar sind. Antworte in derselben Sprache wie der Text im Bild, vorzugsweise Deutsch oder Englisch."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()
