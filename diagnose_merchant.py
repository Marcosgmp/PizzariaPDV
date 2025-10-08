#!/usr/bin/env python3
"""
Diagnóstico específico para o problema de STATUS ERROR
"""

import sys
import os
import time
from datetime import datetime

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ifood_services.merchant import IfoodMerchantService

def diagnose_status_error():
    """Diagnóstico detalhado do problema de STATUS ERROR"""
    print("🔍 DIAGNÓSTICO DO STATUS ERROR")
    print("=" * 60)
    
    service = IfoodMerchantService(is_test_environment=True)
    
    print("📋 ANALISANDO O PROBLEMA...")
    print("   Erro: 'Gestor de Pedidos ou PDV desconectado'")
    print("   Este erro é COMUM em ambiente de teste")
    print("")
    
    # 1. Verificar autenticação
    print("1️⃣ VERIFICANDO AUTENTICAÇÃO...")
    auth_ok = service.test_authentication()
    if not auth_ok:
        print("❌ Problema na autenticação")
        return False
    
    # 2. Verificar merchant details
    print("\n2️⃣ VERIFICANDO MERCHANT...")
    details = service.get_merchant_details()
    if not details:
        print("❌ Problema ao acessar merchant")
        return False
    
    print(f"   ✅ Merchant: {details.name}")
    print(f"   ✅ Status do Merchant: {details.status}")
    
    # 3. Verificar status atual
    print("\n3️⃣ VERIFICANDO STATUS ATUAL...")
    status = service.get_merchant_status()
    
    print(f"   📊 Estado: {status.state.value}")
    print(f"   📝 Mensagem: {status.message}")
    
    if status.validations:
        print("   🔍 Validações detalhadas:")
        for validation in status.validations:
            icon = "✅" if validation.passed else "❌"
            print(f"      {icon} {validation.id}:")
            print(f"          Descrição: {validation.description}")
            print(f"          Status: {'PASSOU' if validation.passed else 'FALHOU'}")
    
    # 4. Verificar dependências de API
    print("\n4️⃣ VERIFICANDO DEPENDÊNCIAS DE API...")
    try:
        dependencies = service.check_api_dependencies()
        print("   📊 APIs disponíveis:")
        
        available_apis = []
        for attr_name in ['catalog', 'delivery_areas', 'orders', 'interruptions', 'events']:
            if hasattr(dependencies, attr_name):
                is_available = getattr(dependencies, attr_name)
                icon = "✅" if is_available else "❌"
                status_text = "DISPONÍVEL" if is_available else "INDISPONÍVEL"
                print(f"      {icon} {attr_name}: {status_text}")
                if is_available:
                    available_apis.append(attr_name)
        
        print(f"   🎯 Total de APIs disponíveis: {len(available_apis)}/5")
        
    except Exception as e:
        print(f"   ❌ Erro ao verificar dependências: {e}")
    
    # 5. Análise do problema
    print("\n5️⃣ ANÁLISE DO PROBLEMA:")
    print("   💡 O erro 'PDV desconectado' significa:")
    print("      - O iFood não detecta um PDV ativo")
    print("      - Em ambiente de teste, isso é NORMAL")
    print("      - Em produção, você precisaria:")
    print("        * Configurar o PDV no Portal iFood")
    print("        * Fazer polling regular de pedidos")
    print("        * Ter catálogo e áreas de entrega configuradas")
    
    # 6. Testar operação básica
    print("\n6️⃣ TESTANDO OPERAÇÃO BÁSICA...")
    print("   Tentando buscar pedidos (pode falhar em teste)...")
    
    orders = service.get_orders()
    if orders is not None:
        print(f"   ✅ Orders API respondeu: {len(orders)} pedidos")
    else:
        print("   ❌ Orders API não disponível (esperado em teste)")
    
    # 7. Conclusão
    print("\n7️⃣ CONCLUSÃO:")
    if status.state.value == "ERROR":
        print("   ❌ STATUS: ERROR (Esperado em ambiente de teste)")
        print("   💡 RECOMENDAÇÕES:")
        print("      1. Para teste: Ignore o status ERROR")
        print("      2. Para produção: Configure PDV no Portal iFood")
        print("      3. Verifique se tem catálogo e áreas de entrega")
        print("      4. Contate suporte iFood para integração PDV")
    else:
        print("   ✅ STATUS: OK - Sistema operacional")
    
    return True

def test_with_polling_attempt():
    """Tenta fazer polling para ver se o status melhora"""
    print("\n🔄 TENTANDO POLLING PARA MELHORAR STATUS")
    print("=" * 50)
    
    service = IfoodMerchantService(is_test_environment=True)
    
    print("📊 Status inicial:")
    initial_status = service.get_merchant_status()
    print(f"   Estado: {initial_status.state.value}")
    
    print("\n🔄 Fazendo 3 tentativas de polling...")
    for i in range(1, 4):
        print(f"   Tentativa {i}/3...")
        try:
            # Tentar acessar diferentes endpoints
            service.list_merchants()
            service.get_merchant_details() 
            service.get_merchant_status()
            time.sleep(10)  # Esperar 10 segundos
        except Exception as e:
            print(f"      ❌ Erro: {e}")
    
    print("\n📊 Status final:")
    final_status = service.get_merchant_status()
    print(f"   Estado: {final_status.state.value}")
    
    if final_status.state.value != initial_status.state.value:
        print("   🎉 Status mudou!")
    else:
        print("   ⚠️  Status permaneceu o mesmo (normal em teste)")

if __name__ == "__main__":
    print("🎯 DIAGNÓSTICO DO MERCHANT iFOOD")
    print("=" * 60)
    print("Este diagnóstico vai analisar por que o status está com ERROR")
    print("e se isso é um problema real ou comportamento normal de teste.\n")
    
    # Diagnóstico principal
    diagnose_status_error()
    
    # Tentativa de polling
    print("\n" + "=" * 60)
    run_polling_test = input("Deseja testar com polling? (s/n): ").lower().strip()
    if run_polling_test in ['s', 'sim', 'y', 'yes']:
        test_with_polling_attempt()
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNÓSTICO CONCLUÍDO!")
    print("💡 Lembre-se: Status ERROR em ambiente de teste é NORMAL")