#!/usr/bin/env python3
"""
Script completo de testes para o Merchant Service iFood
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ifood_services.merchant import IfoodMerchantService, MerchantState

def test_authentication_only():
    """Testa apenas a autenticação"""
    print("🧪 TESTE 1: AUTENTICAÇÃO")
    print("=" * 40)
    
    service = IfoodMerchantService(is_test_environment=True)
    success = service.test_authentication()
    
    if success:
        print("✅ Autenticação: OK")
    else:
        print("❌ Autenticação: FALHOU")
    
    return success

def test_merchant_listing():
    """Testa listagem de merchants"""
    print("\n🧪 TESTE 2: LISTAGEM DE MERCHANTS")
    print("=" * 40)
    
    service = IfoodMerchantService(is_test_environment=True)
    merchants = service.list_merchants()
    
    if merchants:
        print(f"✅ Merchants encontrados: {len(merchants)}")
        for i, merchant in enumerate(merchants, 1):
            print(f"   {i}. {merchant.name} (ID: {merchant.id})")
        return True
    else:
        print("❌ Nenhum merchant encontrado")
        return False

def test_merchant_details():
    """Testa detalhes do merchant"""
    print("\n🧪 TESTE 3: DETALHES DO MERCHANT")
    print("=" * 40)
    
    service = IfoodMerchantService(is_test_environment=True)
    details = service.get_merchant_details()
    
    if details:
        print(f"✅ Detalhes obtidos: {details.name}")
        print(f"   Status: {details.status}")
        print(f"   Ticket Médio: R$ {details.average_ticket:.2f}")
        return True
    else:
        print("❌ Não foi possível obter detalhes")
        return False

def test_merchant_status():
    """Testa status do merchant"""
    print("\n🧪 TESTE 4: STATUS DO MERCHANT")
    print("=" * 40)
    
    service = IfoodMerchantService(is_test_environment=True)
    status = service.get_merchant_status()
    
    if status:
        print(f"✅ Status: {status.state.value}")
        print(f"   Mensagem: {status.message}")
        
        if status.validations:
            print("   Validações:")
            for validation in status.validations:
                icon = "✅" if validation.passed else "❌"
                print(f"     {icon} {validation.id}: {validation.description}")
        
        return status.state != MerchantState.ERROR
    else:
        print("❌ Não foi possível obter status")
        return False

def test_orders_api():
    """Testa API de pedidos"""
    print("\n🧪 TESTE 5: API DE PEDIDOS")
    print("=" * 40)
    
    service = IfoodMerchantService(is_test_environment=True)
    orders = service.get_orders()
    
    if orders is not None:  # Pode ser lista vazia (que é válido)
        print(f"✅ Orders API: OK")
        print(f"   Pedidos encontrados: {len(orders)}")
        return True
    else:
        print("❌ Orders API: Indisponível")
        return False

def test_api_dependencies():
    """Testa todas as dependências de API"""
    print("\n🧪 TESTE 6: DEPENDÊNCIAS DE API")
    print("=" * 40)
    
    service = IfoodMerchantService(is_test_environment=True)
    dependencies = service.check_api_dependencies()
    
    print("📊 Resumo das dependências:")
    available_count = 0
    total = 0
    
    for service_name, is_available in vars(dependencies).items():
        total += 1
        icon = "✅" if is_available else "❌"
        status = "DISPONÍVEL" if is_available else "INDISPONÍVEL"
        print(f"   {icon} {service_name}: {status}")
        if is_available:
            available_count += 1
    
    print(f"\n🎯 Disponibilidade: {available_count}/{total} APIs")
    return available_count > 0

def test_operational_readiness():
    """Teste completo de prontidão operacional"""
    print("\n🧪 TESTE 7: PRONTIDÃO OPERACIONAL")
    print("=" * 40)
    
    service = IfoodMerchantService(is_test_environment=True)
    ready = service.validate_operational_readiness()
    
    if ready:
        print("✅ Sistema pronto para operar!")
    else:
        print("❌ Sistema precisa de ajustes")
    
    return ready

def test_polling_simulation():
    """Simula polling por 2 minutos"""
    print("\n🧪 TESTE 8: SIMULAÇÃO DE POLLING (2 minutos)")
    print("=" * 40)
    
    service = IfoodMerchantService(is_test_environment=True)
    
    print("🔄 Iniciando simulação de polling...")
    print("   Duração: 2 minutos")
    print("   Intervalo: 30 segundos")
    print("   Ctrl+C para interromper\n")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=2)
    poll_count = 0
    
    try:
        while datetime.now() < end_time:
            poll_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            print(f"⏰ Polling #{poll_count} - {current_time}")
            
            # Teste rápido de status
            status = service.get_merchant_status()
            print(f"   Status: {status.state.value}")
            
            # Tempo restante
            remaining = (end_time - datetime.now()).total_seconds()
            if remaining > 0:
                sleep_time = min(30, remaining)  # Máximo 30 segundos
                print(f"   ⏳ Próximo polling em {sleep_time}s...\n")
                time.sleep(sleep_time)
            else:
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Polling interrompido pelo usuário")
    finally:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ Polling finalizado")
        print(f"   Total de pollings: {poll_count}")
        print(f"   Duração total: {duration:.0f} segundos")
    
    return poll_count > 0

def run_ordered_tests():
    """Testes na ordem correta de dependências"""
    print("🧪 TESTES NA ORDEM CORRETA")
    print("=" * 50)
    
    service = IfoodMerchantService(is_test_environment=True)
    
    # PASSO 1: Validar prontidão
    print("\n📋 PASSO 1: VALIDAR PRONTIDÃO")
    ready = service.validate_operational_readiness()
    
    if not ready:
        print("\n❌ Sistema não está pronto para operar")
        print("💡 Verifique as dependências acima")
        return
    
    # PASSO 2: Listar merchants (se disponível)
    print("\n📋 PASSO 2: LISTAR MERCHANTS")
    merchants = service.list_merchants()
    
    # PASSO 3: Detalhes do merchant atual
    print("\n📋 PASSO 3: DETALHES DO MERCHANT")
    service.get_merchant_details()
    
    # PASSO 4: Status atual
    print("\n📋 PASSO 4: STATUS DO MERCHANT") 
    status = service.get_merchant_status()
    
    # PASSO 5: Orders (apenas se status OK)
    if status.state == MerchantState.OK:
        print("\n📋 PASSO 5: PEDIDOS")
        orders = service.get_orders()
    else:
        print(f"\n⏸️  PASSO 5: PEDIDOS (pulado - status: {status.state.value})")
    
    print("\n🎯 TESTES CONCLUÍDOS NA ORDEM CORRETA!")
    
    return service

def run_quick_test():
    """Teste rápido - apenas o essencial"""
    print("🚀 TESTE RÁPIDO DO MERCHANT SERVICE")
    print("=" * 50)
    
    tests = [
        ("Autenticação", test_authentication_only),
        ("Listagem", test_merchant_listing),
        ("Detalhes", test_merchant_details),
        ("Status", test_merchant_status),
        ("Dependências", test_api_dependencies),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Executando: {test_name}...")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        icon = "✅" if result else "❌"
        status = "PASSOU" if result else "FALHOU"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{len(results)} testes passaram")
    
    if passed == len(results):
        print("🎉 Todos os testes passaram! Sistema operacional.")
    else:
        print("💡 Alguns testes falharam. Verifique as configurações.")

def run_comprehensive_test():
    """Teste completo e detalhado"""
    print("🔍 TESTE COMPREENSIVO DO MERCHANT SERVICE")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Executar todos os testes
    tests = [
        ("Autenticação", test_authentication_only),
        ("Listagem", test_merchant_listing),
        ("Detalhes", test_merchant_details), 
        ("Status", test_merchant_status),
        ("Orders API", test_orders_api),
        ("Dependências", test_api_dependencies),
        ("Prontidão", test_operational_readiness),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🎯 {test_name.upper()}")
            print("-" * 40)
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ ERRO: {e}")
            results.append((test_name, False))
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📈 RELATÓRIO FINAL DE TESTES")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        icon = "✅" if result else "❌"
        status = "PASSOU" if result else "FALHOU"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"\n📊 ESTATÍSTICAS:")
    print(f"   Testes executados: {len(results)}")
    print(f"   Testes aprovados: {passed}")
    print(f"   Taxa de sucesso: {(passed/len(results))*100:.1f}%")
    print(f"   Tempo total: {duration:.1f} segundos")
    
    print(f"\n🎯 STATUS FINAL: {'✅ OPERACIONAL' if passed >= 5 else '⚠️  AJUSTES NECESSÁRIOS'}")
    
    if passed >= 5:
        print("💡 Recomendação: Sistema pronto para uso em produção")
    else:
        print("💡 Recomendação: Verificar configurações e credenciais")

def interactive_test():
    """Modo interativo de testes"""
    print("🎮 MODO INTERATIVO DE TESTES")
    print("=" * 50)
    
    service = IfoodMerchantService(is_test_environment=True)
    
    while True:
        print("\n📋 OPÇÕES DE TESTE:")
        print("1. 🔐 Testar Autenticação")
        print("2. 📋 Listar Merchants") 
        print("3. 🏪 Detalhes do Merchant")
        print("4. 📊 Status do Merchant")
        print("5. 📦 Testar Orders API")
        print("6. 🔍 Verificar Dependências")
        print("7. 🎯 Teste de Prontidão")
        print("8. 🔄 Simular Polling (2min)")
        print("9. 🚀 Teste Rápido")
        print("0. ❌ Sair")
        
        choice = input("\nEscolha uma opção (0-9): ").strip()
        
        if choice == "1":
            test_authentication_only()
        elif choice == "2":
            test_merchant_listing()
        elif choice == "3":
            test_merchant_details()
        elif choice == "4":
            test_merchant_status()
        elif choice == "5":
            test_orders_api()
        elif choice == "6":
            test_api_dependencies()
        elif choice == "7":
            test_operational_readiness()
        elif choice == "8":
            test_polling_simulation()
        elif choice == "9":
            run_quick_test()
        elif choice == "0":
            print("👋 Saindo...")
            break
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Testes do Merchant Service iFood')
    parser.add_argument('--quick', action='store_true', help='Teste rápido')
    parser.add_argument('--full', action='store_true', help='Teste completo')
    parser.add_argument('--interactive', action='store_true', help='Modo interativo')
    parser.add_argument('--ordered', action='store_true', help='Teste na ordem correta')
    
    args = parser.parse_args()
    
    if args.quick:
        run_quick_test()
    elif args.full:
        run_comprehensive_test()
    elif args.interactive:
        interactive_test()
    elif args.ordered:
        run_ordered_tests()
    else:
        # Padrão: teste rápido
        print("🎯 TESTES DO MERCHANT SERVICE iFOOD")
        print("Opções disponíveis:")
        print("  --quick       : Teste rápido")
        print("  --full        : Teste completo") 
        print("  --interactive : Modo interativo")
        print("  --ordered     : Teste na ordem correta")
        print("\nExecutando teste rápido...\n")
        run_quick_test()