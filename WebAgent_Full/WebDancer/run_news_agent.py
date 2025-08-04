#!/usr/bin/env python3
"""
Script para ejecutar el agente de búsqueda de noticias con coordenadas
"""

import os
import sys
import json
from datetime import datetime

# Añadir el directorio al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from demos.news_location_agent import NewsLocationAgent
from dotenv import load_dotenv

def main():
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar API keys
    required_keys = ["GOOGLE_SEARCH_KEY", "JINA_API_KEY", "DASHSCOPE_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print("❌ Error: Faltan las siguientes API keys:")
        for key in missing_keys:
            print(f"   - {key}")
        print("\n📝 Para configurarlas:")
        print("1. Edita el archivo .env")
        print("2. Añade las claves que faltan:")
        print("   - GOOGLE_SEARCH_KEY: obtener de https://serper.dev/")
        print("   - JINA_API_KEY: obtener de https://jina.ai/api-dashboard/")
        print("   - DASHSCOPE_API_KEY: obtener de https://dashscope.aliyun.com/")
        return
    
    print("✅ Todas las API keys están configuradas")
    print("\n🚀 Iniciando agente de búsqueda de noticias con geolocalización\n")
    
    # Crear agente
    agent = NewsLocationAgent()
    
    while True:
        print("\n" + "="*60)
        print("Búsqueda de Noticias con Coordenadas Geográficas")
        print("="*60)
        print("\nIngresa las palabras clave para buscar noticias")
        print("(separa múltiples palabras con comas)")
        print("Ejemplos: 'terremoto, Chile' o 'incendio forestal, California'")
        print("Escribe 'salir' para terminar\n")
        
        user_input = input("🔍 Palabras clave: ").strip()
        
        if user_input.lower() == 'salir':
            print("\n👋 ¡Hasta luego!")
            break
        
        if not user_input:
            print("⚠️  Por favor ingresa al menos una palabra clave")
            continue
        
        # Procesar palabras clave
        keywords = [kw.strip() for kw in user_input.split(',')]
        
        try:
            # Buscar noticias
            print(f"\n🔄 Buscando noticias sobre: {', '.join(keywords)}...")
            results = agent.search_news_with_coordinates(keywords)
            
            # Mostrar resultados
            print("\n" + "="*60)
            print("📊 RESULTADOS")
            print("="*60)
            
            if not results:
                print("❌ No se encontraron noticias relevantes")
            else:
                for i, result in enumerate(results, 1):
                    print(f"\n📰 Noticia {i}:")
                    print(f"   Título: {result['title']}")
                    print(f"   URL: {result['url']}")
                    
                    if result['coordinates']:
                        print("   📍 Ubicaciones encontradas:")
                        for coord in result['coordinates']:
                            print(f"      • {coord['location']}")
                            print(f"        Lat: {coord['latitude']}, Lng: {coord['longitude']}")
                            if coord.get('maps_link'):
                                print(f"        🗺️  {coord['maps_link']}")
                    else:
                        print("   ❌ No se encontraron coordenadas específicas")
            
            # Guardar resultados
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"news_results_{timestamp}.json"
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({
                    "query": keywords,
                    "timestamp": timestamp,
                    "results": results
                }, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 Resultados guardados en: {filename}")
            
        except Exception as e:
            print(f"\n❌ Error al procesar la búsqueda: {str(e)}")
            print("Por favor, intenta con otras palabras clave")

if __name__ == "__main__":
    main()