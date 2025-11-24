#!/usr/bin/env python3
"""
INVESTIGACIÓN FORENSE: Exploración de Operaciones del INE

Objetivo: Encontrar las operaciones correctas que contienen:
1. Datos de turismo (Encuesta de Ocupación Hotelera - EOH)
2. Datos de vivienda provincial (Índice de Precios de Vivienda - IPV)
"""

import asyncio
from ine_mcp.api.client import INEClient

async def main():
    print("=" * 80)
    print("INVESTIGACIÓN FORENSE: Operaciones del INE")
    print("=" * 80)
    print()
    
    async with INEClient() as client:
        # Paso 1: Listar todas las operaciones
        print("PASO 1: Lista de operaciones disponibles")
        print("-" * 80)
        
        operations = await client.get_operations()
        print(f"\nTotal operaciones: {len(operations)}\n")
        
        # Buscar operaciones relacionadas con turismo y vivienda
        tourism_ops = []
        housing_ops = []
        
        for op in operations:
            name = op.get('Nombre', '')
            code = op.get('Cod_IOE',op.get('Codigo', ''))
            
            name_lower = name.lower()
            
            if any(word in name_lower for word in ['hotel', 'turismo', 'ocupación', 'pernoctacion', 'viajero']):
                tourism_ops.append({'code': code, 'name': name})
            
            if any(word in name_lower for word in ['vivienda', 'precio', 'alquiler', 'inmobili']):
                housing_ops.append({'code': code, 'name': name})
        
        print(f"📊 Operaciones de TURISMO encontradas: {len(tourism_ops)}")
        for i, op in enumerate(tourism_ops, 1):
            print(f"  {i}. [{op['code']}] {op['name']}")
        
        print()
        print(f"🏠 Operaciones de VIVIENDA encontradas: {len(housing_ops)}")
        for i, op in enumerate(housing_ops, 1):
            print(f"  {i}. [{op['code']}] {op['name']}")
        
        # Paso 2: Explorar series de las operaciones más prometedoras
        print()
        print("=" * 80)
        print("PASO 2: Exploración de Series por Operación")
        print("=" * 80)
        
        # Encuesta de Ocupación Hotelera (normalmente código 26 o similar)
        if tourism_ops:
            print(f"\n🔍 Explorando operación: {tourism_ops[0]['name']}")
            print(f"   Código: {tourism_ops[0]['code']}")
            
            try:
                series = await client.get_operation_series(tourism_ops[0]['code'])
                print(f"   Total series en operación: {len(series)}")
                
                # Filtrar por Málaga
                malaga_series = [s for s in series 
                                 if 'Málaga' in s.get('Nombre', '') 
                                 or 'málaga' in s.get('Nombre', '').lower()]
                
                print(f"   Series con 'Málaga': {len(malaga_series)}")
                
                if malaga_series:
                    print("\n   Primeras 5 series de Málaga:")
                    for i, s in enumerate(malaga_series[:5], 1):
                        print(f"     {i}. {s.get('Nombre', 'Sin nombre')[:70]}")
                        print(f"        ID: {s.get('COD', s.get('Id', 'N/A'))}")
                
                # También buscar Andalucía
                andalucia_series = [s for s in series 
                                    if 'Andalucía' in s.get('Nombre', '')]
                
                print(f"\n   Series con 'Andalucía': {len(andalucia_series)}")
                
                if andalucia_series:
                    print("\n   Primeras 5 series de Andalucía:")
                    for i, s in enumerate(andalucia_series[:5], 1):
                        print(f"     {i}. {s.get('Nombre', 'Sin nombre')[:70]}")
                        print(f"        ID: {s.get('COD', s.get('Id', 'N/A'))}")
                
            except Exception as e:
                print(f"   ✗ Error: {e}")
        
        # Índice de Precios de Vivienda
        if housing_ops:
            print(f"\n🔍 Explorando operación: {housing_ops[0]['name']}")
            print(f"   Código: {housing_ops[0]['code']}")
            
            try:
                series = await client.get_operation_series(housing_ops[0]['code'])
                print(f"   Total series en operación: {len(series)}")
                
                # Filtrar por Málaga
                malaga_series = [s for s in series 
                                 if 'Málaga' in s.get('Nombre', '')]
                
                print(f"   Series con 'Málaga': {len(malaga_series)}")
                
                if malaga_series:
                    print("\n   Primeras 10 series de Málaga:")
                    for i, s in enumerate(malaga_series[:10], 1):
                        print(f"     {i}. {s.get('Nombre', 'Sin nombre')[:70]}")
                        print(f"        ID: {s.get('COD', s.get('Id', 'N/A'))}")
                
                # También Andalucía
                andalucia_series = [s for s in series 
                                    if 'Andalucía' in s.get('Nombre', '')]
                
                print(f"\n   Series con 'Andalucía': {len(andalucia_series)}")
                
                if andalucia_series:
                    print("\n   Primeras 5 series de Andalucía:")
                    for i, s in enumerate(andalucia_series[:5], 1):
                        print(f"     {i}. {s.get('Nombre', 'Sin nombre')[:70]}")
                        print(f"        ID: {s.get('COD', s.get('Id', 'N/A'))}")
                
            except Exception as e:
                print(f"   ✗ Error: {e}")
        
        print()
        print("=" * 80)
        print("CONCLUSIÓN")
        print("=" * 80)
        
        if not tourism_ops:
            print("\n⚠️  No se encontraron operaciones de turismo")
        else:
            print(f"\n✓ Se encontraron {len(tourism_ops)} operaciones de turismo")
        
        if not housing_ops:
            print("\n⚠️  No se encontraron operaciones de vivienda")
        else:
            print(f"\n✓ Se encontraron {len(housing_ops)} operaciones de vivienda")
        
        print("\nSiguientes pasos:")
        print("  1. Usar los códigos de operación encontrados")
        print("  2. Extraer IDs específicos de series de Málaga/Andalucía")
        print("  3. Realizar análisis de correlación con series correctas")
        print()

if __name__ == "__main__":
    asyncio.run(main())
