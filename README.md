# 🕵️ Sistema Automatizado de Inteligencia de Noticias

Sistema de búsqueda automática, análisis y geolocalización de incidentes relacionados con drogas en América del Sur y el Caribe.

## 🎯 Características Principales

- **🔍 Búsqueda Inteligente**: 240+ palabras clave en 7 categorías de drogas
- **🌎 Geolocalización Precisa**: Coordenadas GPS vía Google Maps
- **🔄 Detección de Duplicados**: Algoritmo avanzado de similitud
- **📊 Clasificación Automática**: Relevancia Alta/Media/Baja
- **📈 Exportación Estructurada**: Formato CSV compatible con Centro Regional

## 🚀 Inicio Rápido

### 1. Clonar repositorio
```bash
git clone https://github.com/IAZARA/NoticiasAutomatizado.git
cd NoticiasAutomatizado
```

### 2. Instalar dependencias
```bash
conda create -n drug_intelligence python=3.12
conda activate drug_intelligence
cd Sistema_Inteligencia_Drogas
pip install -r requirements.txt
```

### 3. Configurar APIs
```bash
cp .env.example .env
# Editar .env con tus claves API
```

### 4. Ejecutar sistema
```bash
python run_drug_intelligence.py
```

## 📁 Estructura del Proyecto

```
NoticiasAutomatizado/
├── Sistema_Inteligencia_Drogas/       # Sistema de drogas personalizado
│   ├── drug_intelligence_agent.py     # Motor de inteligencia
│   ├── run_drug_intelligence.py       # Interfaz ejecutora
│   ├── requirements.txt               # Dependencias
│   ├── .env.example                   # Ejemplo de configuración
│   └── README_Sistema_Inteligencia_Drogas.md  # Documentación completa
├── WebAgent_Full/                     # Framework WebAgent completo
│   ├── WebDancer/                     # Agente de búsqueda autónoma
│   ├── WebSailor/                     # Agente de navegación web
│   ├── WebShaper/                     # Síntesis de datos
│   └── WebWalker/                     # Benchmark y evaluación
├── AnalisisArchivo/                   # Archivos de referencia
│   ├── drogas palabras clave.csv     # 240+ keywords
│   ├── paises.csv                    # 57 países objetivo
│   ├── relevancia.csv                # Criterios clasificación
│   └── Centro_Regional_2025 - Base.csv  # Formato salida
├── API_KEYS_IMPORTANTE.txt           # Backup de API keys (NO SUBIR)
└── README.md                          # Este archivo
```

## 🔑 APIs Requeridas

1. **Serper.dev** - Búsqueda en Google (2,500 búsquedas gratis/mes)
2. **Jina AI** - Extracción de contenido web (1M tokens gratis/mes)
3. **DashScope** - Análisis con Qwen2.5-72B

## 📚 Documentación

### Sistema de Inteligencia de Drogas
Ver [README_Sistema_Inteligencia_Drogas.md](Sistema_Inteligencia_Drogas/README_Sistema_Inteligencia_Drogas.md) para documentación completa del sistema personalizado.

### Framework WebAgent Completo
El repositorio incluye el framework WebAgent completo de Alibaba con:
- **WebDancer**: Búsqueda autónoma y Deep Research
- **WebSailor**: Navegación web avanzada 
- **WebShaper**: Síntesis de datos con IA
- **WebWalker**: Benchmarks y evaluación

Consulta [WebAgent_Full/README.md](WebAgent_Full/README.md) para más detalles.

## 📊 Ejemplo de Salida

El sistema genera archivos CSV con:
- Identificadores únicos (CUI)
- Información del incidente
- Clasificación de drogas
- Ubicación granular (País > Provincia > Ciudad)
- Coordenadas GPS precisas
- Detección de duplicados

## 🛡️ Licencia

Este proyecto es de código abierto bajo licencia MIT.

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📞 Soporte

Para reportar issues o sugerir mejoras, usa la sección de [Issues](https://github.com/IAZARA/NoticiasAutomatizado/issues).

---

*Desarrollado con ❤️ para inteligencia de seguridad en América Latina*