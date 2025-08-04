import os
import json
import re
from typing import List, Dict, Tuple
from qwen_agent.tools.base import BaseTool, register_tool
from demos.tools.private.search import Search
from demos.tools.private.visit import Visit
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

@register_tool("google_maps_coordinates")
class GoogleMapsCoordinates(BaseTool):
    name = "google_maps_coordinates"
    description = "Extrae coordenadas de Google Maps para una ubicación específica"
    parameters = {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "La ubicación para buscar en Google Maps"
            }
        },
        "required": ["location"]
    }
    
    def call(self, params: str, **kwargs) -> str:
        try:
            params = self._verify_json_format_args(params)
            location = params["location"]
        except:
            return "[GoogleMaps] Formato de solicitud inválido"
        
        # Buscar en Google Maps
        search_tool = Search()
        search_query = f"Google Maps {location} coordinates latitude longitude"
        search_results = search_tool.call(json.dumps({"query": [search_query]}))
        
        # Buscar enlaces de Google Maps en los resultados
        maps_links = re.findall(r'https://maps\.google\.com[^\s\)]+|https://www\.google\.com/maps[^\s\)]+', search_results)
        
        if maps_links:
            # Visitar el primer enlace de Google Maps
            visit_tool = Visit()
            maps_content = visit_tool.call(json.dumps({
                "url": maps_links[0],
                "goal": f"Encontrar las coordenadas exactas (latitud y longitud) de {location}"
            }))
            
            # Buscar coordenadas en el contenido
            coord_patterns = [
                r'@(-?\d+\.\d+),(-?\d+\.\d+)',  # Formato @lat,lng
                r'latitude["\s:]+(-?\d+\.\d+).*?longitude["\s:]+(-?\d+\.\d+)',
                r'lat["\s:]+(-?\d+\.\d+).*?lng["\s:]+(-?\d+\.\d+)',
                r'(-?\d+\.\d{4,})[,\s]+(-?\d+\.\d{4,})'  # Números decimales largos
            ]
            
            for pattern in coord_patterns:
                matches = re.findall(pattern, maps_content, re.IGNORECASE | re.DOTALL)
                if matches:
                    lat, lng = matches[0]
                    return f"Coordenadas de {location}:\n- Latitud: {lat}\n- Longitud: {lng}\n- Link de Google Maps: {maps_links[0]}"
            
        # Si no encontramos coordenadas directas, buscar información general
        return f"No se pudieron encontrar coordenadas exactas para {location}. Intenta con una búsqueda más específica."


class NewsLocationAgent:
    def __init__(self):
        self.search_tool = Search()
        self.visit_tool = Visit()
        self.maps_tool = GoogleMapsCoordinates()
        
    def search_news(self, keywords: List[str], location_focus: bool = True) -> List[Dict]:
        """
        Busca noticias basadas en palabras clave
        
        Args:
            keywords: Lista de palabras clave para buscar
            location_focus: Si debe enfocarse en encontrar ubicaciones
            
        Returns:
            Lista de noticias con información relevante
        """
        # Construir queries de búsqueda
        queries = []
        base_keywords = " ".join(keywords)
        
        # Query principal
        queries.append(f"{base_keywords} news latest")
        
        # Queries con enfoque en ubicación
        if location_focus:
            queries.append(f"{base_keywords} location where happened")
            queries.append(f"{base_keywords} city country place")
        
        # Realizar búsquedas
        search_results = self.search_tool.call(json.dumps({"query": queries}))
        
        # Parsear resultados
        news_items = []
        sections = search_results.split("\n=======\n")
        
        for section in sections:
            # Extraer enlaces de noticias
            links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', section)
            
            for title, url in links[:3]:  # Top 3 por query
                # Visitar página para extraer detalles
                content = self.visit_tool.call(json.dumps({
                    "url": url,
                    "goal": f"Extraer información sobre: {base_keywords}. Especialmente ubicación, fecha y detalles principales."
                }))
                
                # Extraer ubicaciones del contenido
                locations = self._extract_locations(content)
                
                news_items.append({
                    "title": title,
                    "url": url,
                    "summary": content,
                    "potential_locations": locations
                })
        
        return news_items
    
    def _extract_locations(self, text: str) -> List[str]:
        """Extrae posibles ubicaciones del texto"""
        # Patrones para ciudades, países, lugares
        location_patterns = [
            r'in\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)',
            r'at\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)',
            r'from\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)',
            r'([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)\s+(?:city|town|village|country|state|province)',
        ]
        
        locations = set()
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Limpiar y validar
                location = match.strip()
                if len(location) > 3 and not location.isupper():
                    locations.add(location)
        
        return list(locations)
    
    def get_coordinates_for_news(self, news_item: Dict) -> Dict:
        """Obtiene coordenadas para una noticia específica"""
        result = news_item.copy()
        result["coordinates"] = []
        
        # Intentar con cada ubicación potencial
        for location in news_item.get("potential_locations", []):
            coords_info = self.maps_tool.call(json.dumps({"location": location}))
            
            if "Latitud:" in coords_info:
                # Extraer coordenadas del resultado
                lat_match = re.search(r'Latitud:\s*(-?\d+\.\d+)', coords_info)
                lng_match = re.search(r'Longitud:\s*(-?\d+\.\d+)', coords_info)
                
                if lat_match and lng_match:
                    result["coordinates"].append({
                        "location": location,
                        "latitude": float(lat_match.group(1)),
                        "longitude": float(lng_match.group(1)),
                        "maps_link": re.search(r'Link de Google Maps:\s*(\S+)', coords_info).group(1) if re.search(r'Link de Google Maps:\s*(\S+)', coords_info) else None
                    })
        
        return result
    
    def search_news_with_coordinates(self, keywords: List[str]) -> List[Dict]:
        """
        Función principal: busca noticias y obtiene coordenadas
        
        Args:
            keywords: Lista de palabras clave para buscar
            
        Returns:
            Lista de noticias con coordenadas
        """
        print(f"🔍 Buscando noticias sobre: {', '.join(keywords)}")
        
        # 1. Buscar noticias
        news_items = self.search_news(keywords, location_focus=True)
        print(f"📰 Encontradas {len(news_items)} noticias relevantes")
        
        # 2. Obtener coordenadas para cada noticia
        results = []
        for i, news in enumerate(news_items):
            print(f"\n📍 Procesando noticia {i+1}/{len(news_items)}: {news['title']}")
            result = self.get_coordinates_for_news(news)
            results.append(result)
            
            # Mostrar coordenadas encontradas
            if result["coordinates"]:
                print(f"   ✅ Coordenadas encontradas:")
                for coord in result["coordinates"]:
                    print(f"      - {coord['location']}: ({coord['latitude']}, {coord['longitude']})")
            else:
                print(f"   ❌ No se encontraron coordenadas")
        
        return results


# Ejemplo de uso
if __name__ == "__main__":
    # Verificar que las API keys estén configuradas
    required_keys = ["GOOGLE_SEARCH_KEY", "JINA_API_KEY", "DASHSCOPE_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print(f"❌ Faltan las siguientes API keys: {', '.join(missing_keys)}")
        print("Por favor, configúralas en el archivo .env")
    else:
        # Crear agente
        agent = NewsLocationAgent()
        
        # Buscar noticias con coordenadas
        keywords = ["terremoto", "Japón", "2025"]  # Ejemplo
        results = agent.search_news_with_coordinates(keywords)
        
        # Guardar resultados
        with open("news_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print("\n✅ Resultados guardados en news_results.json")