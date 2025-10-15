# Documentação dos Serviços iFood

## 📋 Índice
- [Visão Geral](#visão-geral)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Serviços iFood](#serviços-ifood)
  - [Auth Service](#auth-service)
  - [Merchant Service](#merchant-service)
  - [Orders Service](#orders-service)
  - [Polling Service](#polling-service)
- [Testes](#testes)
- [Configuração](#configuração)
- [Uso na Aplicação](#uso-na-aplicação)

## 🎯 Visão Geral

Sistema de integração com iFood API para recebimento e processamento automático de pedidos via polling.

## 📁 Estrutura de Arquivos
ifood_services/
├── auth.py # Autenticação com iFood
├── merchant.py # Serviços do merchant
├── orders.py # Serviços de pedidos
├── polling.py # Serviço centralizado de polling
└── init.py

Services/
├── ifood_integration.py # Integração com PDV (Tem que criar)
└── init.py

### ⚙️ Descrição dos Arquivos
auth.py
Gerencia a autenticação com o iFood, obtendo tokens de acesso válidos.
Inclui controle interno de expiração e renovação automática do token.

merchant.py
Realiza operações com estabelecimentos (merchants), como listar lojas, detalhes e status em tempo real.
Também contém recursos de polling para monitorar o status operacional do restaurante.

orders.py
Manipula pedidos iFood (consultas, confirmações, cancelamentos, atualizações de status, etc).
Inclui parsing de dados API, exibição formatada e funções de integração automática para novos pedidos.

polling.py
Gerencia a execução periódica (polling) de serviços do iFood, como recebimento de novos pedidos e sincronização de status.
Suporta callbacks para eventos e monitoramento em tempo real de novas ordens e falhas.

test_auth.py
Script simples para testar autenticação e exibir o token gerado pela API do iFood.

test_ifood_integration.py
Executa uma bateria completa de testes da integração — autenticação, merchants, pedidos e polling — com relatórios coloridos no terminal.

##### Autenticação (auth.py)

```
class IfoodAuthService:
    def get_token(self):
        if self.token and datetime.now() < self.expiration:
            return self.token

        data = {
            "grantType": "client_credentials",
            "clientId": self.client_id,
            "clientSecret": self.client_secret
        }
        resp = requests.post(self.base_url, data=data)
        result = resp.json()
        self.token = result.get("accessToken")
        return self.token
```

##### Pedidos (orders.py)

```
class IfoodOrderService:
    def poll_events(self):
        headers = self._get_headers()
        resp = requests.get(f"{self.base_url}/events:polling", headers=headers)
        return [OrderEvent(**e) for e in resp.json()]

    def confirm_order(self, order_id):
        resp = requests.post(f"{self.base_url}/orders/{order_id}/confirm", headers=self._get_headers())
        return resp.status_code == 204
```

##### Merchant (merchant.py)
```
class IfoodMerchantService:
    def list_merchants(self):
        resp = requests.get(f"{self.base_url}/merchants", headers=self._get_headers())
        return [m["name"] for m in resp.json()]

    def get_merchant_status(self):
        resp = requests.get(f"{self.base_url}/merchants/{self.merchant_id}/status", headers=self._get_headers())
        return resp.json()

```
##### Polling Automático (polling.py)

```
class IfoodPollingService:
    def start_polling(self):
        for poll_type in self.config:
            thread = threading.Thread(target=self._polling_worker, args=(poll_type,))
            thread.start()
        print("Serviços de polling iniciados!")

    def _poll_orders(self):
        events = self.orders_service.poll_events()
        for e in events:
            if e.code == EventCode.PLC:
                order = self.orders_service.get_order_details(e.order_id)
                self._notify_callbacks('new_order', {'order': order})

```

##### Teste de Integração Completa (test_ifood_integration.py)
python test_ifood_integration.py --completo

