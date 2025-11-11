import requests
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import IFOOD_API_URL, IFOOD_MERCHANT_ID
from ifood_services.auth import IfoodAuthService

class ItemType(str, Enum):
    DEFAULT = "DEFAULT"
    PIZZA = "PIZZA"
    COMBO_V2 = "COMBO_V2"

class ItemStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"

class OptionGroupType(str, Enum):
    SIZE = "SIZE"
    TOPPING = "TOPPING"
    CRUST = "CRUST"
    EDGE = "EDGE"
    OFFER_UNIT = "OFFER_UNIT"
    CUTLERY = "CUTLERY"
    SPECIFICATION = "SPECIFICATION"
    INGREDIENTS = "INGREDIENTS"

class CatalogContext(str, Enum):
    DEFAULT = "DEFAULT"
    WHITELABEL = "WHITELABEL"

@dataclass
class Price:
    value: float
    originalValue: Optional[float] = None

@dataclass
class CatalogPrice:
    value: float
    originalValue: Optional[float] = None
    catalogContext: CatalogContext

@dataclass
class CatalogStatus:
    status: ItemStatus
    catalogContext: CatalogContext

@dataclass
class CatalogExternalCode:
    externalCode: str
    catalogContext: CatalogContext

@dataclass
class ContextModifier:
    parentOptionId: Optional[str] = None
    catalogContext: Optional[CatalogContext] = None
    status: Optional[ItemStatus] = None
    price: Optional[Price] = None
    externalCode: Optional[str] = None

@dataclass
class Product:
    id: str
    name: str
    externalCode: Optional[str] = None
    description: Optional[str] = None
    imagePath: Optional[str] = None
    quantity: Optional[int] = None
    optionGroups: List[Dict] = field(default_factory=list)

@dataclass
class Option:
    id: str
    productId: str
    status: ItemStatus = ItemStatus.AVAILABLE
    externalCode: Optional[str] = None
    index: Optional[int] = None
    price: Optional[Price] = None
    fractions: List[int] = field(default_factory=list)
    contextModifiers: List[ContextModifier] = field(default_factory=list)

@dataclass
class OptionGroup:
    id: str
    name: str
    optionGroupType: OptionGroupType
    optionIds: List[str]
    status: ItemStatus = ItemStatus.AVAILABLE
    externalCode: Optional[str] = None
    index: Optional[int] = None
    min: Optional[int] = None
    max: Optional[int] = None
    type: Optional[str] = None  # Para combos

@dataclass
class Item:
    id: str
    type: ItemType
    status: ItemStatus
    productId: str
    externalCode: Optional[str] = None
    categoryId: Optional[str] = None
    index: Optional[int] = None
    price: Optional[Price] = None

@dataclass
class Category:
    id: str
    name: str
    externalCode: Optional[str] = None
    status: ItemStatus = ItemStatus.AVAILABLE
    order: Optional[int] = None

@dataclass
class Catalog:
    id: str
    name: str
    description: Optional[str] = None
    status: str = "AVAILABLE"

class IfoodCatalogService:
    """
    iFood Catalog API Service
    =========================
    
    Serviço para gerenciamento completo do catálogo iFood
    Especializado em pizzas e combos para PDV centralizado
    """
    
    def __init__(self, is_test_environment: bool = True):
        self.base_url = f"{IFOOD_API_URL}/catalog/v2.0"
        self.merchant_id = IFOOD_MERCHANT_ID
        self.auth_service = IfoodAuthService()
        self.headers = {
            "Content-Type": "application/json"
        }
        self.is_test_environment = is_test_environment
        
        if is_test_environment:
            print("AMBIENTE DE TESTE DETECTADO - Catalog Service")

    def _get_headers(self):
        """Get headers with current access token"""
        token = self.auth_service.get_token()
        return {
            **self.headers,
            "Authorization": f"Bearer {token}"
        }

    def _generate_id(self):
        """Gera UUID para entidades do catálogo"""
        return str(uuid.uuid4())

    # CATALOGOS
    def list_catalogs(self) -> List[Catalog]:
        """Lista todos os catálogos - GET /merchants/{merchantId}/catalogs"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/catalogs"
        
        try:
            headers = self._get_headers()
            print("Listando catálogos...")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            catalogs = []
            for catalog_data in data:
                catalog = Catalog(
                    id=catalog_data.get("id", ""),
                    name=catalog_data.get("name", ""),
                    description=catalog_data.get("description", ""),
                    status=catalog_data.get("status", "AVAILABLE")
                )
                catalogs.append(catalog)

            print(f"Encontrados {len(catalogs)} catálogo(s)")
            return catalogs

        except Exception as e:
            print(f"Erro ao listar catálogos: {e}")
            return []

    # CATEGORIAS
    def list_categories(self, catalog_id: str) -> List[Category]:
        """Lista categorias de um catálogo - GET /merchants/{merchantId}/catalogs/{catalogId}/categories"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/catalogs/{catalog_id}/categories"
        
        try:
            headers = self._get_headers()
            print(f"Listando categorias do catálogo {catalog_id}...")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            categories = []
            for category_data in data:
                category = Category(
                    id=category_data.get("id", ""),
                    name=category_data.get("name", ""),
                    externalCode=category_data.get("externalCode"),
                    status=ItemStatus(category_data.get("status", "AVAILABLE")),
                    order=category_data.get("order")
                )
                categories.append(category)

            print(f"Encontradas {len(categories)} categoria(s)")
            return categories

        except Exception as e:
            print(f"Erro ao listar categorias: {e}")
            return []

    def create_category(self, catalog_id: str, name: str, external_code: str = None) -> Optional[Category]:
        """Cria uma categoria - POST /merchants/{merchantId}/catalogs/{catalogId}/categories"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/catalogs/{catalog_id}/categories"
        
        payload = {
            "name": name,
            "externalCode": external_code or f"cat_{int(datetime.now().timestamp())}",
            "status": "AVAILABLE"
        }
        
        try:
            headers = self._get_headers()
            print(f"Criando categoria '{name}'...")
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            category = Category(
                id=data.get("id"),
                name=data.get("name"),
                externalCode=data.get("externalCode"),
                status=ItemStatus(data.get("status", "AVAILABLE"))
            )
            
            print(f"Categoria criada: ID {category.id}")
            return category

        except Exception as e:
            print(f"Erro ao criar categoria: {e}")
            return None

    # ITENS - OPERAÇÕES COMPLETAS
    def create_or_update_item(self, item_data: Dict) -> bool:
        """Cria ou atualiza um item completo - PUT /merchants/{merchantId}/items"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/items"
        
        try:
            headers = self._get_headers()
            print("Enviando item para catálogo...")
            resp = requests.put(url, json=item_data, headers=headers, timeout=15)
            resp.raise_for_status()
            print("Item criado/atualizado com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao criar/atualizar item: {e}")
            return False

    def create_pizza_item(self, name: str, base_price: float, category_id: str = None) -> bool:
        """Cria um item de pizza com estrutura completa"""
        
        # Gera IDs para todas as entidades
        item_id = self._generate_id()
        product_id = self._generate_id()
        
        # IDs para grupos de opções
        size_group_id = self._generate_id()
        crust_group_id = self._generate_id()
        edge_group_id = self._generate_id()
        topping_group_id = self._generate_id()
        
        # IDs para produtos
        traditional_crust_id = self._generate_id()
        thin_crust_id = self._generate_id()
        traditional_edge_id = self._generate_id()
        stuffed_edge_id = self._generate_id()
        medium_size_id = self._generate_id()
        large_size_id = self._generate_id()
        calabresa_id = self._generate_id()
        marguerita_id = self._generate_id()
        
        # IDs para opções
        medium_option_id = self._generate_id()
        large_option_id = self._generate_id()
        traditional_crust_option_id = self._generate_id()
        thin_crust_option_id = self._generate_id()
        traditional_edge_option_id = self._generate_id()
        stuffed_edge_option_id = self._generate_id()
        calabresa_option_id = self._generate_id()
        marguerita_option_id = self._generate_id()

        payload = {
            "item": {
                "id": item_id,
                "type": "PIZZA",
                "status": "AVAILABLE",
                "externalCode": f"pizza_{name.lower().replace(' ', '_')}",
                "index": 0,
                "productId": product_id
            },
            "products": [
                {
                    "id": product_id,
                    "externalCode": f"pizza_{name.lower().replace(' ', '_')}_prod",
                    "name": name,
                    "optionGroups": [
                        {"id": size_group_id, "min": 1, "max": 1},
                        {"id": crust_group_id, "min": 1, "max": 1},
                        {"id": edge_group_id, "min": 1, "max": 1},
                        {"id": topping_group_id, "min": 1, "max": 2}
                    ]
                },
                {
                    "id": traditional_crust_id,
                    "externalCode": "massa_tradicional",
                    "name": "Massa Tradicional"
                },
                {
                    "id": thin_crust_id,
                    "externalCode": "massa_fina",
                    "name": "Massa Fina"
                },
                {
                    "id": traditional_edge_id,
                    "externalCode": "borda_tradicional",
                    "name": "Borda Tradicional"
                },
                {
                    "id": stuffed_edge_id,
                    "externalCode": "borda_recheada",
                    "name": "Borda Recheada"
                },
                {
                    "id": medium_size_id,
                    "externalCode": "tamanho_medio",
                    "name": "Média (8 pedaços)",
                    "quantity": 8
                },
                {
                    "id": large_size_id,
                    "externalCode": "tamanho_grande",
                    "name": "Grande (12 pedaços)",
                    "quantity": 12
                },
                {
                    "id": calabresa_id,
                    "externalCode": "calabresa",
                    "name": "Calabresa"
                },
                {
                    "id": marguerita_id,
                    "externalCode": "marguerita",
                    "name": "Marguerita"
                }
            ],
            "optionGroups": [
                {
                    "id": size_group_id,
                    "name": "Tamanhos",
                    "externalCode": "tamanhos_pizza",
                    "status": "AVAILABLE",
                    "index": 0,
                    "optionGroupType": "SIZE",
                    "optionIds": [medium_option_id, large_option_id]
                },
                {
                    "id": crust_group_id,
                    "name": "Massas",
                    "externalCode": "massas_pizza",
                    "status": "AVAILABLE",
                    "index": 1,
                    "optionGroupType": "CRUST",
                    "optionIds": [traditional_crust_option_id, thin_crust_option_id]
                },
                {
                    "id": edge_group_id,
                    "name": "Bordas",
                    "externalCode": "bordas_pizza",
                    "status": "AVAILABLE",
                    "index": 2,
                    "optionGroupType": "EDGE",
                    "optionIds": [traditional_edge_option_id, stuffed_edge_option_id]
                },
                {
                    "id": topping_group_id,
                    "name": "Sabores",
                    "externalCode": "sabores_pizza",
                    "status": "AVAILABLE",
                    "index": 3,
                    "optionGroupType": "TOPPING",
                    "optionIds": [calabresa_option_id, marguerita_option_id]
                }
            ],
            "options": [
                {
                    "id": medium_option_id,
                    "status": "AVAILABLE",
                    "productId": medium_size_id,
                    "fractions": [1],
                    "externalCode": "pizza_media",
                    "price": {"value": base_price, "originalValue": base_price * 1.2}
                },
                {
                    "id": large_option_id,
                    "status": "AVAILABLE",
                    "productId": large_size_id,
                    "fractions": [1, 2],
                    "externalCode": "pizza_grande",
                    "price": {"value": base_price * 1.5, "originalValue": base_price * 1.8}
                },
                {
                    "id": traditional_crust_option_id,
                    "status": "AVAILABLE",
                    "productId": traditional_crust_id,
                    "externalCode": "massa_trad",
                    "price": {"value": 0, "originalValue": 0}
                },
                {
                    "id": thin_crust_option_id,
                    "status": "AVAILABLE",
                    "productId": thin_crust_id,
                    "externalCode": "massa_fina",
                    "price": {"value": 2, "originalValue": 3}
                },
                {
                    "id": traditional_edge_option_id,
                    "status": "AVAILABLE",
                    "productId": traditional_edge_id,
                    "externalCode": "borda_trad",
                    "price": {"value": 0, "originalValue": 0}
                },
                {
                    "id": stuffed_edge_option_id,
                    "status": "AVAILABLE",
                    "productId": stuffed_edge_id,
                    "externalCode": "borda_rech",
                    "price": {"value": 5, "originalValue": 7}
                },
                {
                    "id": calabresa_option_id,
                    "status": "AVAILABLE",
                    "index": 0,
                    "productId": calabresa_id,
                    "externalCode": "calabresa_op",
                    "contextModifiers": [
                        {
                            "parentOptionId": medium_option_id,
                            "catalogContext": "DEFAULT",
                            "status": "AVAILABLE",
                            "price": {"value": 0, "originalValue": 0}
                        },
                        {
                            "parentOptionId": large_option_id,
                            "catalogContext": "DEFAULT",
                            "status": "AVAILABLE", 
                            "price": {"value": 0, "originalValue": 0}
                        }
                    ]
                },
                {
                    "id": marguerita_option_id,
                    "status": "AVAILABLE",
                    "index": 1,
                    "productId": marguerita_id,
                    "externalCode": "marguerita_op",
                    "contextModifiers": [
                        {
                            "parentOptionId": medium_option_id,
                            "catalogContext": "DEFAULT",
                            "status": "AVAILABLE",
                            "price": {"value": 2, "originalValue": 3}
                        },
                        {
                            "parentOptionId": large_option_id,
                            "catalogContext": "DEFAULT",
                            "status": "AVAILABLE",
                            "price": {"value": 3, "originalValue": 4}
                        }
                    ]
                }
            ]
        }

        return self.create_or_update_item(payload)

    # ATUALIZAÇÕES DE PREÇO
    def update_item_price(self, item_id: str, price: float, catalog_context: CatalogContext = None) -> bool:
        """Altera preço de um item - PATCH /merchants/{merchantId}/items/price"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/items/price"
        
        payload = {
            "itemId": item_id,
            "price": price
        }
        
        if catalog_context:
            payload["priceByCatalog"] = [{
                "value": price,
                "catalogContext": catalog_context.value
            }]
            del payload["price"]
        
        try:
            headers = self._get_headers()
            print(f"Atualizando preço do item {item_id}...")
            resp = requests.patch(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            print("Preço do item atualizado com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao atualizar preço do item: {e}")
            return False

    def update_option_price(self, option_id: str, price: float, parent_customization_option_id: str = None, 
                          catalog_context: CatalogContext = None) -> bool:
        """Altera preço de um complemento - PATCH /merchants/{merchantId}/options/price"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/options/price"
        
        payload = {
            "optionId": option_id,
            "price": price
        }
        
        if parent_customization_option_id:
            payload["parentCustomizationOptionId"] = parent_customization_option_id
        
        if catalog_context:
            payload["priceByCatalog"] = [{
                "value": price,
                "catalogContext": catalog_context.value
            }]
            del payload["price"]
        
        try:
            headers = self._get_headers()
            print(f"Atualizando preço da opção {option_id}...")
            resp = requests.patch(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            print("Preço da opção atualizado com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao atualizar preço da opção: {e}")
            return False

    # ATUALIZAÇÕES DE STATUS
    def update_item_status(self, item_id: str, status: ItemStatus, catalog_context: CatalogContext = None) -> bool:
        """Altera status de um item - PATCH /merchants/{merchantId}/items/status"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/items/status"
        
        payload = {
            "itemId": item_id,
            "status": status.value
        }
        
        if catalog_context:
            payload["statusByCatalog"] = [{
                "status": status.value,
                "catalogContext": catalog_context.value
            }]
            del payload["status"]
        
        try:
            headers = self._get_headers()
            print(f"Atualizando status do item {item_id}...")
            resp = requests.patch(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            print("Status do item atualizado com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao atualizar status do item: {e}")
            return False

    def update_option_status(self, option_id: str, status: ItemStatus, parent_customization_option_id: str = None,
                           catalog_context: CatalogContext = None) -> bool:
        """Altera status de um complemento - PATCH /merchants/{merchantId}/options/status"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/options/status"
        
        payload = {
            "optionId": option_id,
            "status": status.value
        }
        
        if parent_customization_option_id:
            payload["parentCustomizationOptionId"] = parent_customization_option_id
        
        if catalog_context:
            payload["statusByCatalog"] = [{
                "status": status.value,
                "catalogContext": catalog_context.value
            }]
            del payload["status"]
        
        try:
            headers = self._get_headers()
            print(f"Atualizando status da opção {option_id}...")
            resp = requests.patch(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            print("Status da opção atualizado com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao atualizar status da opção: {e}")
            return False

    # UPLOAD DE IMAGENS
    def upload_image(self, image_path: str) -> Optional[str]:
        """Faz upload de imagens - POST /merchants/{merchantId}/image/upload"""
        url = f"{self.base_url}/merchants/{self.merchant_id}/image/upload"
        
        try:
            headers = self._get_headers()
            # Remove Content-Type para multipart form data
            headers.pop("Content-Type", None)
            
            with open(image_path, 'rb') as image_file:
                files = {'file': (os.path.basename(image_path), image_file, 'image/jpeg')}
                print(f"Fazendo upload da imagem {image_path}...")
                resp = requests.post(url, files=files, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                
                image_id = data.get("id")
                print(f"Imagem enviada com sucesso: ID {image_id}")
                return image_id

        except Exception as e:
            print(f"Erro ao fazer upload da imagem: {e}")
            return None

def run_catalog_tests():
    """Testes básicos do Catalog Service"""
    print("TESTES CATALOG SERVICE")
    print("=" * 60)
    
    catalog_service = IfoodCatalogService(is_test_environment=True)
    
    print("1. LISTANDO CATÁLOGOS")
    print("-" * 30)
    catalogs = catalog_service.list_catalogs()
    
    if catalogs:
        catalog_id = catalogs[0].id
        print(f"Catálogo selecionado: {catalogs[0].name} (ID: {catalog_id})")
        
        print("\n2. LISTANDO CATEGORIAS")
        print("-" * 30)
        categories = catalog_service.list_categories(catalog_id)
        
        print("\n3. CRIANDO CATEGORIA")
        print("-" * 30)
        new_category = catalog_service.create_category(catalog_id, "Pizzas Teste")
        
        print("\n4. CRIANDO ITEM DE PIZZA")
        print("-" * 30)
        success = catalog_service.create_pizza_item("Pizza Teste", 35.90)
        if success:
            print("Pizza criada com sucesso!")
        else:
            print("Falha ao criar pizza")
    
    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Servico Catalog iFood')
    parser.add_argument('--test', action='store_true', help='Executar testes básicos')
    
    args = parser.parse_args()
    
    if args.test:
        run_catalog_tests()