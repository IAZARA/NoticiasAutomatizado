import os
import csv
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
from qwen_agent.tools.base import BaseTool, register_tool
from tools.private.search import Search
from tools.private.visit import Visit
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

@dataclass
class DrugIncident:
    """Estructura para un incidente de drogas detectado"""
    cui: str
    titulo: str
    descripcion: str
    fecha_publicacion: str
    medio: str
    url: str
    pais_origen: str
    relevancia: str
    keywords: List[str]
    categoria_sustancia: str
    tipo_sustancia: str
    cantidad: str
    unidad: str
    ubicacion_granular: Dict[str, str]  # pais, provincia, distrito
    coordenadas: Dict[str, str]  # geo_pais, geo_prov, geo_distrito
    duplicado_de: Optional[str] = None
    similarity_score: float = 0.0

class DrugKeywordManager:
    """Gestor de palabras clave de drogas"""
    
    def __init__(self, keywords_file: str):
        self.categories = {}
        self.all_keywords = []
        self._load_keywords(keywords_file)
    
    def _load_keywords(self, file_path: str):
        """Carga las palabras clave desde el CSV"""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Primera fila son las categorías
            
            # Inicializar categorías
            for header in headers:
                self.categories[header] = []
            
            # Cargar palabras clave
            for row in reader:
                for i, keyword in enumerate(row):
                    if keyword.strip():
                        category = headers[i]
                        self.categories[category].append(keyword.strip())
                        self.all_keywords.append(keyword.strip().lower())
    
    def get_search_queries(self, time_limit: str = "última semana") -> List[str]:
        """Genera queries de búsqueda optimizadas"""
        base_terms = ["incautación", "decomiso", "captura", "detención", "operativo", "droga"]
        location_terms = ["América del Sur", "Sudamérica", "Caribe", "Latinoamérica"]
        
        queries = []
        
        # Queries por categoría principal con limitador temporal y geográfico
        priority_substances = ["fentanilo", "tusi", "metanfetamina", "cocaína", "marihuana"]
        
        for substance in priority_substances:
            for base_term in base_terms[:3]:  # Solo los 3 términos más efectivos
                query = f"{substance} {base_term} {time_limit} site:-.com OR site:-.co OR site:-.ar OR site:-.br OR site:-.pe OR site:-.cl OR site:-.mx"
                queries.append(query)
        
        return queries[:15]  # Limitar a 15 queries para no exceder tokens

class CountryManager:
    """Gestor de países y regiones objetivo"""
    
    def __init__(self, countries_file: str):
        self.countries = {}
        self.target_regions = ["America del Sur", "Caribe"]
        self._load_countries(countries_file)
    
    def _load_countries(self, file_path: str):
        """Carga los países objetivo desde el CSV"""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Region'] in self.target_regions:
                    self.countries[row['Pais_Origen']] = {
                        'codigo': row['alpha-2_Completo'],
                        'region': row['Region'],
                        'coordenadas': row['Geo']
                    }
    
    def is_target_country(self, country_name: str) -> bool:
        """Verifica si un país está en el scope objetivo"""
        country_name = country_name.lower()
        for country in self.countries:
            if country.lower() in country_name or country_name in country.lower():
                return True
        return False
    
    def get_country_info(self, country_name: str) -> Optional[Dict]:
        """Obtiene información del país"""
        for country, info in self.countries.items():
            if country.lower() in country_name.lower() or country_name.lower() in country.lower():
                return {"name": country, **info}
        return None

class RelevanceClassifier:
    """Clasificador de relevancia de noticias"""
    
    def __init__(self, relevance_file: str):
        self.criteria = self._load_criteria(relevance_file)
    
    def _load_criteria(self, file_path: str) -> Dict:
        """Carga criterios de relevancia"""
        return {
            "alta": {
                "title_indicators": ["incautación", "decomiso", "captura", "operativo", "detención"],
                "quantity_indicators": ["toneladas", "kilos", "kilogramos", "millones"],
                "international_indicators": ["cartel", "internacional", "frontera"]
            },
            "media": {
                "body_indicators": ["droga", "narcótico", "estupefaciente", "sustancia"],
                "local_indicators": ["local", "municipal", "barrio"]
            },
            "baja": {
                "reference_indicators": ["mencionó", "según", "reportó", "indicó"]
            }
        }
    
    def classify(self, title: str, content: str, keywords: List[str]) -> str:
        """Clasifica la relevancia de una noticia"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Relevancia ALTA: aparece en título con palabras clave importantes
        alta_score = 0
        for indicator in self.criteria["alta"]["title_indicators"]:
            if indicator in title_lower:
                alta_score += 2
        
        for keyword in keywords:
            if keyword.lower() in title_lower:
                alta_score += 1
        
        if alta_score >= 3:
            return "Alta"
        
        # Relevancia MEDIA: aparece en cuerpo del texto
        media_score = 0
        for indicator in self.criteria["media"]["body_indicators"]:
            if indicator in content_lower:
                media_score += 1
        
        if media_score >= 2:
            return "Media"
        
        # Por defecto: Baja
        return "Baja"

class DuplicateDetector:
    """Detector de noticias duplicadas"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.processed_incidents = []
    
    def is_duplicate(self, incident: DrugIncident) -> Tuple[bool, Optional[str], float]:
        """Detecta si un incidente es duplicado"""
        for existing in self.processed_incidents:
            similarity = self._calculate_similarity(incident, existing)
            
            if similarity >= self.similarity_threshold:
                return True, existing.cui, similarity
        
        return False, None, 0.0
    
    def _calculate_similarity(self, incident1: DrugIncident, incident2: DrugIncident) -> float:
        """Calcula similitud entre dos incidentes"""
        # Similitud por ubicación (40%)
        location_sim = self._location_similarity(
            incident1.ubicacion_granular,
            incident2.ubicacion_granular
        ) * 0.4
        
        # Similitud por fecha (30%)
        date_sim = self._date_similarity(
            incident1.fecha_publicacion,
            incident2.fecha_publicacion
        ) * 0.3
        
        # Similitud por contenido (30%)
        content_sim = self._content_similarity(
            incident1.titulo + " " + incident1.descripcion,
            incident2.titulo + " " + incident2.descripcion
        ) * 0.3
        
        return location_sim + date_sim + content_sim
    
    def _location_similarity(self, loc1: Dict, loc2: Dict) -> float:
        """Compara similitud de ubicaciones"""
        if loc1.get('distrito') and loc2.get('distrito'):
            if loc1['distrito'].lower() == loc2['distrito'].lower():
                return 1.0
        
        if loc1.get('provincia') and loc2.get('provincia'):
            if loc1['provincia'].lower() == loc2['provincia'].lower():
                return 0.8
        
        if loc1.get('pais') and loc2.get('pais'):
            if loc1['pais'].lower() == loc2['pais'].lower():
                return 0.5
        
        return 0.0
    
    def _date_similarity(self, date1: str, date2: str) -> float:
        """Compara similitud de fechas"""
        try:
            d1 = datetime.strptime(date1, "%d/%m/%Y")
            d2 = datetime.strptime(date2, "%d/%m/%Y")
            diff = abs((d1 - d2).days)
            
            if diff == 0:
                return 1.0
            elif diff <= 1:
                return 0.8
            elif diff <= 3:
                return 0.5
            else:
                return 0.0
        except:
            return 0.0
    
    def _content_similarity(self, content1: str, content2: str) -> float:
        """Compara similitud de contenido"""
        return SequenceMatcher(None, content1.lower(), content2.lower()).ratio()
    
    def add_incident(self, incident: DrugIncident):
        """Añade un incidente procesado"""
        self.processed_incidents.append(incident)

@register_tool("google_maps_precise_coordinates")
class GoogleMapsPreciseCoordinates(BaseTool):
    name = "google_maps_precise_coordinates"
    description = "Obtiene coordenadas precisas de Google Maps para ubicaciones específicas"
    parameters = {
        "type": "object",
        "properties": {
            "country": {"type": "string", "description": "País"},
            "province": {"type": "string", "description": "Provincia/Estado"},
            "district": {"type": "string", "description": "Ciudad/Municipio/Distrito"}
        },
        "required": ["country"]
    }
    
    def call(self, params: str, **kwargs) -> str:
        try:
            params = self._verify_json_format_args(params)
            country = params["country"]
            province = params.get("province", "")
            district = params.get("district", "")
        except:
            return "[GoogleMaps] Formato inválido"
        
        # Construir query de búsqueda jerarquizada
        location_parts = [part for part in [district, province, country] if part]
        search_location = ", ".join(location_parts)
        
        search_tool = Search()
        search_query = f"Google Maps {search_location} coordinates exact location"
        search_results = search_tool.call(json.dumps({"query": [search_query]}))
        
        # Buscar enlaces de Google Maps
        maps_links = re.findall(r'https://(?:maps\.google\.com|www\.google\.com/maps)[^\s\)]+', search_results)
        
        if maps_links:
            visit_tool = Visit()
            maps_content = visit_tool.call(json.dumps({
                "url": maps_links[0],
                "goal": f"Extraer coordenadas exactas (latitud, longitud) de {search_location}"
            }))
            
            # Patrones para extraer coordenadas
            coord_patterns = [
                r'@(-?\d+\.\d+),(-?\d+\.\d+)',
                r'latitude["\s:]+(-?\d+\.\d+).*?longitude["\s:]+(-?\d+\.\d+)',
                r'(-?\d+\.\d{4,})[,\s]+(-?\d+\.\d{4,})'
            ]
            
            for pattern in coord_patterns:
                matches = re.findall(pattern, maps_content, re.IGNORECASE | re.DOTALL)
                if matches:
                    lat, lng = matches[0]
                    return json.dumps({
                        "found": True,
                        "coordinates": {"latitude": lat, "longitude": lng},
                        "location": search_location,
                        "maps_url": maps_links[0]
                    })
        
        return json.dumps({
            "found": False,
            "coordinates": {"latitude": "", "longitude": ""},
            "location": search_location,
            "maps_url": ""
        })

class DrugIntelligenceAgent:
    """Agente especializado en inteligencia de drogas"""
    
    def __init__(self, base_path: str = "/Users/macbook/Documents/WebSearchAgent/AnalisisArchivo"):
        self.keyword_manager = DrugKeywordManager(f"{base_path}/drogas palabras clave.csv")
        self.country_manager = CountryManager(f"{base_path}/paises.csv")
        self.relevance_classifier = RelevanceClassifier(f"{base_path}/relevancia.csv")
        self.duplicate_detector = DuplicateDetector()
        
        self.search_tool = Search()
        self.visit_tool = Visit()
        self.maps_tool = GoogleMapsPreciseCoordinates()
        
        self.cui_counter = 1
    
    def search_drug_incidents(self, days_back: int = 7) -> List[DrugIncident]:
        """Busca incidentes de drogas en el período especificado"""
        print(f"🔍 Iniciando búsqueda de incidentes de drogas (últimos {days_back} días)")
        
        # Generar queries optimizadas
        queries = self.keyword_manager.get_search_queries(f"últimos {days_back} días")
        
        incidents = []
        processed_urls = set()
        
        print(f"📊 Ejecutando {len(queries)} búsquedas especializadas...")
        
        # Realizar búsquedas
        search_results = self.search_tool.call(json.dumps({"query": queries}))
        sections = search_results.split("\n=======\n")
        
        for section in sections:
            # Extraer enlaces de noticias
            links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', section)
            
            for title, url in links:
                if url in processed_urls:
                    continue
                processed_urls.add(url)
                
                # Verificar si es de país objetivo
                if not self._is_relevant_by_country(title + " " + section):
                    continue
                
                print(f"📄 Analizando: {title[:60]}...")
                
                # Visitar página para obtener contenido completo
                content = self.visit_tool.call(json.dumps({
                    "url": url,
                    "goal": "Extraer información completa sobre incidente de drogas: fecha, ubicación específica (país, provincia, ciudad), tipo de droga, cantidad decomisada, autoridades involucradas"
                }))
                
                # Procesar el incidente
                incident = self._process_incident(title, content, url, section)
                
                if incident and self._is_valid_incident(incident):
                    # Verificar duplicados
                    is_dup, dup_cui, similarity = self.duplicate_detector.is_duplicate(incident)
                    
                    if is_dup:
                        incident.duplicado_de = dup_cui
                        incident.similarity_score = similarity
                        print(f"   ⚠️  Duplicado detectado (similitud: {similarity:.2f}) con {dup_cui}")
                    else:
                        self.duplicate_detector.add_incident(incident)
                    
                    incidents.append(incident)
                    print(f"   ✅ Incidente procesado: {incident.cui}")
        
        print(f"\n🎯 Procesamiento completado: {len(incidents)} incidentes encontrados")
        return incidents
    
    def _is_relevant_by_country(self, text: str) -> bool:
        """Verifica si el texto menciona países objetivo"""
        text_lower = text.lower()
        
        # Verificar países específicos
        target_countries = ["argentina", "brazil", "brasil", "chile", "colombia", "peru", "perú", 
                          "ecuador", "bolivia", "uruguay", "paraguay", "venezuela", "guyana",
                          "suriname", "mexico", "méxico", "guatemala", "honduras", "nicaragua",
                          "costa rica", "panama", "panamá", "cuba", "jamaica", "dominicana"]
        
        return any(country in text_lower for country in target_countries)
    
    def _process_incident(self, title: str, content: str, url: str, search_context: str) -> Optional[DrugIncident]:
        """Procesa un incidente individual"""
        try:
            # Generar CUI único
            cui = f"A{self.cui_counter:07d}"
            self.cui_counter += 1
            
            # Extraer información básica
            fecha = self._extract_date(content)
            medio = self._extract_media_source(url)
            pais = self._extract_country(content + " " + search_context)
            
            # Extraer palabras clave relevantes
            keywords = self._extract_keywords(title + " " + content)
            
            # Clasificar relevancia
            relevancia = self.relevance_classifier.classify(title, content, keywords)
            
            # Extraer información de drogas
            categoria_sustancia, tipo_sustancia = self._extract_drug_info(title + " " + content)
            cantidad, unidad = self._extract_quantity(content)
            
            # Extraer ubicación granular
            ubicacion = self._extract_granular_location(content, pais)
            
            # Obtener coordenadas
            coordenadas = self._get_coordinates(ubicacion)
            
            incident = DrugIncident(
                cui=cui,
                titulo=title,
                descripcion=self._extract_description(content),
                fecha_publicacion=fecha,
                medio=medio,
                url=url,
                pais_origen=pais,
                relevancia=relevancia,
                keywords=keywords,
                categoria_sustancia=categoria_sustancia,
                tipo_sustancia=tipo_sustancia,
                cantidad=cantidad,
                unidad=unidad,
                ubicacion_granular=ubicacion,
                coordenadas=coordenadas
            )
            
            return incident
            
        except Exception as e:
            print(f"   ❌ Error procesando incidente: {str(e)}")
            return None
    
    def _extract_date(self, content: str) -> str:
        """Extrae fecha de publicación"""
        # Patrones de fecha
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            if matches:
                day, month, year = matches[0]
                return f"{day}/{month}/{year}"
        
        # Fecha actual si no se encuentra
        return datetime.now().strftime("%d/%m/%Y")
    
    def _extract_media_source(self, url: str) -> str:
        """Extrae fuente del medio"""
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return domain_match.group(1) if domain_match else "Unknown"
    
    def _extract_country(self, text: str) -> str:
        """Extrae país del texto"""
        for country, info in self.country_manager.countries.items():
            if country.lower() in text.lower():
                return country
        return "Sin especificar"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrae palabras clave relevantes"""
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.keyword_manager.all_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:10]  # Máximo 10 keywords
    
    def _extract_drug_info(self, text: str) -> Tuple[str, str]:
        """Extrae categoría y tipo de droga"""
        text_lower = text.lower()
        
        for category, keywords in self.keyword_manager.categories.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return category, keyword
        
        return "Sin especificar", "Sin especificar"
    
    def _extract_quantity(self, text: str) -> Tuple[str, str]:
        """Extrae cantidad y unidad"""
        quantity_patterns = [
            r'(\d+(?:\.\d+)?)\s*(kilogramos?|kg|gramos?|gr|toneladas?|t|libras?|lb)',
            r'(\d+(?:\.\d+)?)\s*(pastillas?|dosis|frascos?|envoltorios?|bolsas?)'
        ]
        
        for pattern in quantity_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                cantidad, unidad = matches[0]
                return cantidad, unidad
        
        return "0,00", "Sin datos"
    
    def _extract_granular_location(self, text: str, country: str) -> Dict[str, str]:
        """Extrae ubicación granular (país, provincia, distrito)"""
        # Patrones para extraer ubicaciones
        location_patterns = [
            r'en\s+([A-Z][a-zA-Z\s]+),\s*([A-Z][a-zA-Z\s]+)',
            r'municipio\s+de\s+([A-Z][a-zA-Z\s]+)',
            r'ciudad\s+de\s+([A-Z][a-zA-Z\s]+)',
            r'provincia\s+de\s+([A-Z][a-zA-Z\s]+)',
            r'departamento\s+de\s+([A-Z][a-zA-Z\s]+)'
        ]
        
        ubicacion = {"pais": country, "provincia": "", "distrito": ""}
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    distrito, provincia = matches[0]
                    ubicacion["distrito"] = distrito.strip()
                    ubicacion["provincia"] = provincia.strip()
                else:
                    ubicacion["distrito"] = matches[0].strip()
                break
        
        return ubicacion
    
    def _get_coordinates(self, ubicacion: Dict[str, str]) -> Dict[str, str]:
        """Obtiene coordenadas para la ubicación"""
        coords_result = self.maps_tool.call(json.dumps(ubicacion))
        
        try:
            coords_data = json.loads(coords_result)
            if coords_data.get("found"):
                return {
                    "geo_pais": f"{coords_data['coordinates']['latitude']}, {coords_data['coordinates']['longitude']}",
                    "geo_prov": f"{coords_data['coordinates']['latitude']}, {coords_data['coordinates']['longitude']}",
                    "geo_distrito": f"{coords_data['coordinates']['latitude']}, {coords_data['coordinates']['longitude']}"
                }
        except:
            pass
        
        return {"geo_pais": "", "geo_prov": "", "geo_distrito": ""}
    
    def _extract_description(self, content: str) -> str:
        """Extrae descripción relevante"""
        # Tomar primeras líneas del contenido limpio
        lines = content.split('\n')
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if len(line) > 20 and not line.startswith('['):
                description_lines.append(line)
                if len(description_lines) >= 3:
                    break
        
        return ' '.join(description_lines)[:500]
    
    def _is_valid_incident(self, incident: DrugIncident) -> bool:
        """Valida si un incidente es válido"""
        return (
            incident.titulo and
            incident.pais_origen != "Sin especificar" and
            incident.relevancia in ["Alta", "Media", "Baja"] and
            len(incident.keywords) > 0
        )
    
    def export_to_csv(self, incidents: List[DrugIncident], filename: str):
        """Exporta incidentes a CSV con formato del sistema"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_filename = f"{filename}_{timestamp}.csv"
        
        fieldnames = [
            'Articulo_ID', 'CUI', 'Fecha_Publicacion_Articulo', 'Titulo_Articulo',
            'Descripcion_Articulo', 'Medio', 'URL_Acortada', 'Pais_Origen_Articulo',
            'Cod_Continente', 'Idioma', 'Categoria_tematica', 'Relevancia_Mencion',
            'Frecuencia_Mencion', 'Impacto_Articulo', 'Keywords',
            'Clasificacion_Sust_Estup_Decomisada', 'Tipo_Sus_Estup_Decomisada',
            'Cant_Sust_Estup_Sintetica_incautada', 'Unidad', 'Fueza_interviniente',
            'Ubicacion_Secuestro', 'Region', 'Sub region', 'Pais', 'Provincia',
            'Distrito', 'Alfa_2', 'ISO_3166_2', 'Geo_Pais', 'Geo_Prov',
            'Geo_Distrito', 'Fecha', 'Dia', 'Semana', 'Quincena', 'Mes_Largo',
            'Trimestre', 'Año', 'Duplicado_De', 'Similarity_Score'
        ]
        
        with open(full_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for incident in incidents:
                # Procesar fecha
                try:
                    fecha_obj = datetime.strptime(incident.fecha_publicacion, "%d/%m/%Y")
                except:
                    fecha_obj = datetime.now()
                
                row = {
                    'Articulo_ID': incident.cui,
                    'CUI': incident.cui,
                    'Fecha_Publicacion_Articulo': incident.fecha_publicacion,
                    'Titulo_Articulo': incident.titulo,
                    'Descripcion_Articulo': incident.descripcion,
                    'Medio': incident.medio,
                    'URL_Acortada': incident.url,
                    'Pais_Origen_Articulo': incident.pais_origen,
                    'Cod_Continente': 'SA',
                    'Idioma': 'ES',
                    'Categoria_tematica': 'Incidente',
                    'Relevancia_Mencion': incident.relevancia,
                    'Frecuencia_Mencion': 'Media',
                    'Impacto_Articulo': 'Medio',
                    'Keywords': ', '.join(incident.keywords),
                    'Clasificacion_Sust_Estup_Decomisada': incident.categoria_sustancia,
                    'Tipo_Sus_Estup_Decomisada': incident.tipo_sustancia,
                    'Cant_Sust_Estup_Sintetica_incautada': incident.cantidad,
                    'Unidad': incident.unidad,
                    'Fueza_interviniente': '',
                    'Ubicacion_Secuestro': incident.ubicacion_granular.get('distrito', ''),
                    'Region': 'America',
                    'Sub region': 'America del Sur',
                    'Pais': incident.ubicacion_granular.get('pais', ''),
                    'Provincia': incident.ubicacion_granular.get('provincia', ''),
                    'Distrito': incident.ubicacion_granular.get('distrito', ''),
                    'Alfa_2': '',
                    'ISO_3166_2': '',
                    'Geo_Pais': incident.coordenadas.get('geo_pais', ''),
                    'Geo_Prov': incident.coordenadas.get('geo_prov', ''),
                    'Geo_Distrito': incident.coordenadas.get('geo_distrito', ''),
                    'Fecha': incident.fecha_publicacion,
                    'Dia': fecha_obj.day,
                    'Semana': fecha_obj.isocalendar()[1],
                    'Quincena': 1 if fecha_obj.day <= 15 else 2,
                    'Mes_Largo': fecha_obj.strftime('%B'),
                    'Trimestre': f'T{((fecha_obj.month-1)//3)+1}',
                    'Año': fecha_obj.year,
                    'Duplicado_De': incident.duplicado_de or '',
                    'Similarity_Score': f"{incident.similarity_score:.2f}" if incident.similarity_score else ''
                }
                
                writer.writerow(row)
        
        print(f"📊 Datos exportados a: {full_filename}")
        return full_filename

# Ejemplo de uso
if __name__ == "__main__":
    agent = DrugIntelligenceAgent()
    
    # Buscar incidentes de la última semana
    incidents = agent.search_drug_incidents(days_back=7)
    
    # Exportar resultados
    if incidents:
        filename = agent.export_to_csv(incidents, "drug_intelligence_report")
        
        # Mostrar resumen
        print(f"\n📈 RESUMEN DEL ANÁLISIS:")
        print(f"   Total incidentes: {len(incidents)}")
        print(f"   Duplicados detectados: {len([i for i in incidents if i.duplicado_de])}")
        print(f"   Por relevancia:")
        
        relevancia_count = {}
        for incident in incidents:
            relevancia_count[incident.relevancia] = relevancia_count.get(incident.relevancia, 0) + 1
        
        for relevancia, count in relevancia_count.items():
            print(f"     - {relevancia}: {count}")
        
        print(f"   Archivo generado: {filename}")
    else:
        print("❌ No se encontraron incidentes en el período especificado")