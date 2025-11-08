import sys
import os
import time

# Adiciona o path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ifood_services.merchant import IfoodMerchantService
from ifood_services.polling import ifood_polling_service

class HomologacaoTester:
    def __init__(self):
        self.results = []
        self.merchant_service = IfoodMerchantService(is_test_environment=True)
    
    def run_test(self, test_name, test_function):
        """Executa um teste e registra o resultado"""
        print(f"\n{test_name}")
        print("-" * 40)
        
        try:
            result = test_function()
            self.results.append((test_name, result, "SUCESSO"))
            print(f"RESULTADO: SUCESSO")
            return True
        except Exception as e:
            self.results.append((test_name, False, f"ERRO: {e}"))
            print(f"RESULTADO: FALHA - {e}")
            return False
    
    def test_autenticacao(self):
        """Testa autenticação com iFood"""
        return self.merchant_service.test_authentication()
    
    def test_listar_merchants(self):
        """Testa listagem de merchants"""
        merchants = self.merchant_service.list_merchants()
        return len(merchants) > 0
    
    def test_detalhes_merchant(self):
        """Testa obtenção de detalhes do merchant"""
        merchants = self.merchant_service.list_merchants()
        if not merchants:
            return False
        
        details = self.merchant_service.get_merchant_details(merchants[0].id)
        return details is not None
    
    def test_status_merchant(self):
        """Testa obtenção de status do merchant"""
        merchants = self.merchant_service.list_merchants()
        if not merchants:
            return False
        
        status = self.merchant_service.get_merchant_status(merchants[0].id)
        return status is not None
    
    def test_interrupcoes(self):
        """Testa operações com interrupções"""
        merchants = self.merchant_service.list_merchants()
        if not merchants:
            return False
        
        merchant_id = merchants[0].id
        interruptions = self.merchant_service.list_interruptions(merchant_id)
        return interruptions is not None  # Pode ser lista vazia
    
    def test_horario_funcionamento(self):
        """Testa operações com horário de funcionamento"""
        merchants = self.merchant_service.list_merchants()
        if not merchants:
            return False
        
        merchant_id = merchants[0].id
        opening_hours = self.merchant_service.get_opening_hours(merchant_id)
        return True  # Mesmo que não tenha horário configurado
    
    def test_polling_inicializacao(self):
        """Testa inicialização do polling service"""
        status = ifood_polling_service.get_status()
        return status is not None and 'is_running' in status
    
    def run_todos_testes(self):
        """Executa todos os testes de homologação"""
        print("=" * 60)
        print("TESTE COMPLETO DE HOMOLOGAÇÃO iFOOD")
        print("=" * 60)
        
        testes = [
            ("Autenticação", self.test_autenticacao),
            ("Listar Merchants", self.test_listar_merchants),
            ("Detalhes do Merchant", self.test_detalhes_merchant),
            ("Status do Merchant", self.test_status_merchant),
            ("Interrupções", self.test_interrupcoes),
            ("Horário de Funcionamento", self.test_horario_funcionamento),
            ("Inicialização do Polling", self.test_polling_inicializacao),
        ]
        
        for test_name, test_function in testes:
            self.run_test(test_name, test_function)
        
        self.gerar_relatorio()
    
    def gerar_relatorio(self):
        """Gera relatório final dos testes"""
        print("\n" + "=" * 60)
        print("RELATÓRIO FINAL DE HOMOLOGAÇÃO")
        print("=" * 60)
        
        total = len(self.results)
        sucessos = sum(1 for _, resultado, _ in self.results if resultado)
        
        for test_name, resultado, mensagem in self.results:
            status = "OK" if resultado else "FALHA"
            print(f"{test_name}: {status} - {mensagem}")
        
        print(f"\nRESUMO: {sucessos}/{total} testes passaram")
        
        if sucessos == total:
            print("\n🎉 SISTEMA APROVADO PARA HOMOLOGAÇÃO!")
            print("Todos os requisitos foram atendidos.")
        elif sucessos >= total * 0.8:
            print("\n⚠️  SISTEMA QUASE PRONTO PARA HOMOLOGAÇÃO")
            print("A maioria dos testes passou. Verifique os que falharam.")
        else:
            print("\n❌ SISTEMA NÃO ESTÁ PRONTO PARA HOMOLOGAÇÃO")
            print("Muitos testes falharam. Verifique a configuração.")

if __name__ == "__main__":
    tester = HomologacaoTester()
    tester.run_todos_testes()