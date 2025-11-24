#!/usr/bin/env python3
"""
Ejemplo Simple: Búsqueda de Series del INE

Este script demuestra cómo usar la búsqueda semántica para encontrar
series estadísticas del INE sin necesidad de conocer los IDs exactos.

Autor: INE MCP Server
Licencia: MIT
"""

import asyncio
from pathlib import Path
from ine_mcp.embeddings.search import SemanticSearchEngine

async def main():
    print("=" * 80)
    print("EJEMPLO: Búsqueda Semántica en el INE")
    print("=" * 80)
    print()
    
    # Inicializar el motor de búsqueda
    search_engine = SemanticSearchEngine(
        index_path=Path("/app/data/faiss_index.bin"),
        metadata_path=Path("/app/data/series_metadata.pkl"),
    )
    
    try:
        search_engine.load_index()
        stats = search_engine.get_stats()
        print(f"✓ Índice cargado: {stats['total_series']:,} series disponibles")
    except Exception as e:
        print(f"✗ Error cargando índice: {e}")
        print("\nAsegúrate de que el índice está construido ejecutando:")
        print("  uv run python scripts/build_index.py")
        return
    
    print()
    print("Ejemplos de búsquedas semánticas:")
    print("-" * 80)
    
    # Lista de consultas de ejemplo
    queries = [
        ("Inflación mensual", "Encuentra índices de precios al consumidor"),
        ("Desempleo por comunidades", "Encuentra datos de paro por regiones"),
        ("Precio de la vivienda", "Encuentra índices de precios inmobiliarios"),
        ("Turistas extranjeros", "Encuentra datos de visitantes internacionales"),
        ("Salario medio España", "Encuentra datos salariales"),
    ]
    
    for query, description in queries:
        print(f"\n🔍 Consulta: '{query}'")
        print(f"   {description}")
        print()
        
        results = search_engine.search(query, top_k=3, score_threshold=0.5)
        
        if not results:
            print("   ℹ️  No se encontraron resultados con score > 0.5")
            continue
        
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['name'][:65]}...")
            print(f"      ID: {result['id']} | Similitud: {result['similarity_score']:.3f}")
    
    print()
    print("=" * 80)
    print("CONCLUSIÓN")
    print("=" * 80)
    print()
    print("La búsqueda semántica permite encontrar series relevantes usando")
    print("lenguaje natural, sin necesidad de conocer códigos específicos.")
    print()
    print("Próximos pasos:")
    print("  1. Usa los IDs encontrados para obtener datos con get_series_data()")
    print("  2. Analiza las series con el DataAggregator")
    print("  3. Calcula correlaciones entre diferentes variables")
    print()

if __name__ == "__main__":
    asyncio.run(main())
