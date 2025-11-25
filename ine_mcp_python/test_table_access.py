#!/usr/bin/env python3
"""
PRUEBA: Acceso a tablas del INE usando get_table_data

IDs de tablas conocidas:
- 24051: IPV (Índice de Precios de Vivienda)
- 50902: IPC General
- 10882: Salarios (Encuesta Anual de Estructura Salarial)
"""

import asyncio
from ine_mcp.api.client import INEClient
import json

async def main():
    print("=" * 80)
    print("PRUEBA: Acceso a Tablas del INE")
    print("=" * 80)
    print()
    
    async with INEClient() as client:
        # Probar tabla del IPV
        print("1. Probando IPV (Índice de Precios de Vivienda) - Tabla 24051")
        print("-" * 80)
        
        try:
            print("  Solicitando datos...")
            data = await client.get_table_data("24051")
            
            print(f"  ✓ Datos recibidos")
            print(f"  Tipo: {type(data)}")
            
            if isinstance(data, dict):
                print(f"\n  Claves en la respuesta: {list(data.keys())[:10]}")
                
                # Intentar extraer información relevante
                if "Data" in data:
                    print(f"  Puntos de datos: {len(data['Data'])}")
                    print(f"\n  Primeros 3 datos:")
                    for i, point in enumerate(data["Data"][:3], 1):
                        print(f"    {i}. {point}")
                
                elif "Nombre" in data:
                    print(f"  Nombre: {data.get('Nombre', 'N/A')}")
                
                # Guardar respuesta completa
                with open("/app/ipv_table_24051.json", "w") as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"\n  ✓ Datos guardados en: /app/ipv_table_24051.json")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Probar tabla del IPC
        print()
        print("2. Probando IPC General - Tabla 50902")
        print("-" * 80)
        
        try:
            print("  Solicitando datos...")
            data = await client.get_table_data("50902")
            
            print(f"  ✓ Datos recibidos")
            print(f"  Tipo: {type(data)}")
            
            if isinstance(data, dict):
                print(f"\n  Claves: {list(data.keys())[:10]}")
                
                if "Data" in data:
                    print(f"  Puntos de datos: {len(data['Data'])}")
                
                with open("/app/ipc_table_50902.json", "w") as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"\n  ✓ Datos guardados en: /app/ipc_table_50902.json")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Probar tabla de salarios
        print()
        print("3. Probando Salarios - Tabla 10882")
        print("-" * 80)
        
        try:
            print("  Solicitando datos...")
            data = await client.get_table_data("10882")
            
            print(f"  ✓ Datos recibidos")
            print(f"  Tipo: {type(data)}")
            
            if isinstance(data, dict):
                print(f"\n  Claves: {list(data.keys())[:10]}")
                
                if "Data" in data:
                    print(f"  Puntos de datos: {len(data.get('Data', []))}")
                
                with open("/app/salary_table_10882.json", "w") as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"\n  ✓ Datos guardados en: /app/salary_table_10882.json")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print()
    print("=" * 80)
    print("FIN DE LA PRUEBA")
    print("=" * 80)
    print("\nSi alguna tabla tiene datos, puedes copiarlos con:")
    print("  docker cp ine_mcp_python-ine-mcp-1:/app/ipv_table_24051.json ./")
    print()

if __name__ == "__main__":
    asyncio.run(main())
