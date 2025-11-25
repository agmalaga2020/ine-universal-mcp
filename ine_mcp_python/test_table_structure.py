#!/usr/bin/env python3
"""
Prueba mejorada: Ver estructura de datos de tablas
"""

import asyncio
from ine_mcp.api.client import INEClient
import json

async def main():
    print("PRUEBA: Estructura de datos de tablas del INE\n")
    
    async with INEClient() as client:
        # Probar IPV
        print("1. IPV (Tabla 24051) - Últimos 10 datos")
        print("-" * 60)
        
        try:
            data = await client._request("GET", "/DATOS_TABLA/24051", params={"nult": 10})
            
            print(f"Tipo: {type(data)}")
            
            if isinstance(data, list):
                print(f"Elementos: {len(data)}")
                print(f"\nPrimer elemento:")
                if data:
                    print(json.dumps(data[0], indent=2, ensure_ascii=False))
                
                    if len(data) >= 2:
                        print(f"\nSegundo elemento:")
                        print(json.dumps(data[1], indent=2, ensure_ascii=False))
            
            elif isinstance(data, dict):
                print(f"Claves: {list(data.keys())}")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
            
        except Exception as e:
            print(f"Error: {e}")
        
        print()
        
        # Probar IPC
        print("2. IPC (Tabla 50902) - Últimos 10 datos")
        print("-" * 60)
        
        try:
            data = await client._request("GET", "/DATOS_TABLA/50902", params={"nult": 10})
            
            print(f"Tipo: {type(data)}")
            
            if isinstance(data, list) and data:
                print(f"Elementos: {len(data)}")
                print(f"\nPrimer elemento:")
                print(json.dumps(data[0], indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
