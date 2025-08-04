#!/usr/bin/env python3
"""
Sistema de Inteligencia de Drogas - WebAgent
Busca, analiza y geolocaliza incidentes de drogas en América del Sur y Caribe
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Añadir el directorio al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from drug_intelligence_agent import DrugIntelligenceAgent

def print_banner():
    """Imprime banner del sistema"""
    print("\n" + "="*80)
    print("🕵️  SISTEMA DE INTELIGENCIA DE DROGAS - WebAgent")
    print("   Búsqueda Automática de Incidentes en América del Sur y Caribe")
    print("="*80)

def verify_setup():
    """Verifica que el sistema esté correctamente configurado"""
    # Verificar APIs
    required_keys = ["GOOGLE_SEARCH_KEY", "JINA_API_KEY", "DASHSCOPE_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print("❌ Error: Faltan API keys:")
        for key in missing_keys:
            print(f"   - {key}")
        return False
    
    # Verificar archivos de configuración
    base_path = "/Users/macbook/Documents/WebSearchAgent/AnalisisArchivo"
    required_files = [
        "drogas palabras clave.csv",
        "paises.csv", 
        "relevancia.csv",
        "Centro_Regional_2025 - Base.csv"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(f"{base_path}/{file}"):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Error: Faltan archivos de configuración:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def show_system_info():
    """Muestra información del sistema"""
    print("\n📊 CONFIGURACIÓN DEL SISTEMA:")
    print("   🌎 Región objetivo: América del Sur y Caribe (México hacia abajo)")
    print("   🕐 Período: Última semana por defecto")
    print("   🔍 Categorías de drogas: 7 tipos, ~240 palabras clave")
    print("   📍 Geolocalización: Coordenadas precisas via Google Maps")
    print("   🔄 Detección de duplicados: Algoritmo de similitud avanzado")
    print("   📈 Relevancia: Alta/Media/Baja según criterios predefinidos")

def run_intelligence_scan(days_back: int = 7):
    """Ejecuta escaneo de inteligencia"""
    print(f"\n🚀 INICIANDO ESCANEO DE INTELIGENCIA")
    print(f"   Período: Últimos {days_back} días")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Crear agente
        print("\n🔧 Inicializando agente especializado...")
        agent = DrugIntelligenceAgent()
        
        # Realizar búsqueda
        print("\n🔍 Ejecutando búsqueda inteligente...")
        incidents = agent.search_drug_incidents(days_back=days_back)
        
        if not incidents:
            print("\n❌ No se encontraron incidentes en el período especificado")
            return
        
        # Generar reporte
        print(f"\n📊 GENERANDO REPORTE...")
        filename = agent.export_to_csv(incidents, "drug_intelligence_report")
        
        # Mostrar estadísticas
        show_statistics(incidents)
        
        print(f"\n✅ ESCANEO COMPLETADO")
        print(f"   📄 Archivo generado: {filename}")
        print(f"   🕐 Duración: {datetime.now().strftime('%H:%M:%S')}")
        
        return filename
        
    except Exception as e:
        print(f"\n❌ ERROR DURANTE EL ESCANEO: {str(e)}")
        return None

def show_statistics(incidents):
    """Muestra estadísticas del análisis"""
    print(f"\n📈 ESTADÍSTICAS DEL ANÁLISIS:")
    print(f"   📰 Total incidentes procesados: {len(incidents)}")
    
    # Duplicados
    duplicates = [i for i in incidents if i.duplicado_de]
    if duplicates:
        print(f"   🔄 Duplicados detectados: {len(duplicates)}")
        for dup in duplicates[:3]:  # Mostrar primeros 3
            print(f"      - {dup.cui} (similar a {dup.duplicado_de}, {dup.similarity_score:.2f})")
        if len(duplicates) > 3:
            print(f"      - ... y {len(duplicates)-3} más")
    
    # Por relevancia
    relevancia_stats = {}
    for incident in incidents:
        relevancia_stats[incident.relevancia] = relevancia_stats.get(incident.relevancia, 0) + 1
    
    print(f"   🎯 Distribución por relevancia:")
    for relevancia, count in relevancia_stats.items():
        percentage = (count / len(incidents)) * 100
        print(f"      - {relevancia}: {count} ({percentage:.1f}%)")
    
    # Por país
    country_stats = {}
    for incident in incidents:
        country_stats[incident.pais_origen] = country_stats.get(incident.pais_origen, 0) + 1
    
    print(f"   🌍 Top países con incidentes:")
    sorted_countries = sorted(country_stats.items(), key=lambda x: x[1], reverse=True)
    for country, count in sorted_countries[:5]:
        print(f"      - {country}: {count}")
    
    # Por tipo de droga
    drug_stats = {}
    for incident in incidents:
        if incident.tipo_sustancia != "Sin especificar":
            drug_stats[incident.tipo_sustancia] = drug_stats.get(incident.tipo_sustancia, 0) + 1
    
    if drug_stats:
        print(f"   💊 Top sustancias detectadas:")
        sorted_drugs = sorted(drug_stats.items(), key=lambda x: x[1], reverse=True)
        for drug, count in sorted_drugs[:5]:
            print(f"      - {drug}: {count}")
    
    # Coordenadas encontradas
    with_coords = [i for i in incidents if i.coordenadas.get('geo_pais')]
    print(f"   📍 Con coordenadas precisas: {len(with_coords)} ({(len(with_coords)/len(incidents)*100):.1f}%)")

def interactive_mode():
    """Modo interactivo"""
    while True:
        print("\n" + "="*60)
        print("🔧 OPCIONES DEL SISTEMA")
        print("="*60)
        print("1. 🔍 Escaneo rápido (últimos 3 días)")
        print("2. 📅 Escaneo semanal (últimos 7 días)")
        print("3. 📊 Escaneo extendido (últimos 14 días)")
        print("4. ⚙️  Escaneo personalizado")
        print("5. 📋 Ver configuración del sistema")
        print("6. 🚪 Salir")
        
        choice = input("\n👉 Selecciona una opción (1-6): ").strip()
        
        if choice == "1":
            run_intelligence_scan(days_back=3)
        elif choice == "2":
            run_intelligence_scan(days_back=7)
        elif choice == "3":
            run_intelligence_scan(days_back=14)
        elif choice == "4":
            try:
                days = int(input("📅 Ingresa número de días atrás (1-30): "))
                if 1 <= days <= 30:
                    run_intelligence_scan(days_back=days)
                else:
                    print("⚠️  Rango válido: 1-30 días")
            except ValueError:
                print("⚠️  Por favor ingresa un número válido")
        elif choice == "5":
            show_system_info()
        elif choice == "6":
            print("\n👋 Sistema finalizado. ¡Hasta luego!")
            break
        else:
            print("⚠️  Opción no válida. Intenta de nuevo.")

def main():
    """Función principal"""
    # Cargar configuración
    load_dotenv()
    
    # Banner
    print_banner()
    
    # Verificar configuración
    print("\n🔧 Verificando configuración del sistema...")
    if not verify_setup():
        print("\n❌ Sistema no configurado correctamente. Por favor verifica la configuración.")
        return
    
    print("✅ Sistema configurado correctamente")
    
    # Mostrar información
    show_system_info()
    
    # Modo interactivo
    interactive_mode()

if __name__ == "__main__":
    main()