#!/usr/bin/env python3
"""
Descargar y analizar estructura de tabla 25171 (IPV)
"""

import asyncio
import json
from ine_mcp.api.client import INEClient

async def main():
    print("Descargando tabla 25171 (Índice de Precios de Vivienda)...\n")
    
    async with INEClient() as client:
        data = await client.get_table_data("25171")
    
    print("=" * 80)
    print("ESTRUCTURA DEL JSON")
    print("=" * 80)
    print()
    
    # Analizar tipo y claves principales
    print(f"Tipo: {type(data)}")
    print()
    
    if isinstance(data, dict):
        print(f"Claves principales ({len(data)} total):")
        for key in data.keys():
            value = data[key]
            print(f"  • {key}: {type(value).__name__}", end="")
            
            if isinstance(value, list):
                print(f" (longitud: {len(value)})")
                if len(value) > 0:
                    print(f"    Primer elemento: {type(value[0]).__name__}")
                    if isinstance(value[0], dict):
                        print(f"    Claves: {list(value[0].keys())[:5]}")
            elif isinstance(value, dict):
                print(f" ({len(value)} claves)")
            else:
                print()
        
        print()
        print("=" * 80)
        print("MUESTRA DE DATOS")
        print("=" * 80)
        print()
        
        # Mostrar Data si existe
        if "Data" in data:
            print(f"'Data' contiene {len(data['Data'])} elementos")
            print("\nPrimeros 3 elementos:")
            for i, item in enumerate(data["Data"][:3], 1):
                print(f"\n{i}. {json.dumps(item, indent=2, ensure_ascii=False)}")
        
        # Mostrar MetaData si existe
        if "MetaData" in data:
            print(f"\n'MetaData' contiene:")
            print(json.dumps(data["MetaData"], indent=2, ensure_ascii=False)[:500])
        
        # Guardar JSON completo
        with open("/app/table_25171_full.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print()
        print("=" * 80)
        print(f"✓ JSON completo guardado en: /app/table_25171_full.json")
        print(f"  Tamaño: {len(json.dumps(data))} caracteres")
        print("=" * 80)
    
    elif isinstance(data, list):
        print(f"Es una lista con {len(data)} elementos")
        print("\nPrimer elemento:")
        print(json.dumps(data[0], indent=2, ensure_ascii=False))
        
        with open("/app/table_25171_full.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    print()

if __name__ == "__main__":
    asyncio.run(main())
