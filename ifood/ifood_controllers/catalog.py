from fastapi import APIRouter, HTTPException, status, UploadFile, File
from typing import List, Optional
from ifood_services.catalog import (
    IfoodCatalogService, Catalog, Category, ItemType, ItemStatus, 
    CatalogContext, Price
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

catalog_service = IfoodCatalogService(is_test_environment=True)

@router.get("/catalogs", response_model=List[Catalog])
def list_catalogs():
    """Lista todos os catálogos"""
    catalogs = catalog_service.list_catalogs()
    if not catalogs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum catálogo encontrado"
        )
    return catalogs

@router.get("/catalogs/{catalog_id}/categories", response_model=List[Category])
def list_categories(catalog_id: str):
    """Lista categorias de um catálogo"""
    categories = catalog_service.list_categories(catalog_id)
    if not categories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma categoria encontrada"
        )
    return categories

@router.post("/catalogs/{catalog_id}/categories", response_model=Category)
def create_category(catalog_id: str, name: str, external_code: Optional[str] = None):
    """Cria uma nova categoria"""
    category = catalog_service.create_category(catalog_id, name, external_code)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar categoria"
        )
    return category

@router.put("/items")
def create_or_update_item(item_data: dict):
    """Cria ou atualiza um item completo"""
    success = catalog_service.create_or_update_item(item_data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar/atualizar item"
        )
    return {"success": True, "message": "Item criado/atualizado com sucesso"}

@router.post("/items/pizza")
def create_pizza_item(name: str, base_price: float, category_id: Optional[str] = None):
    """Cria um item de pizza com estrutura completa"""
    success = catalog_service.create_pizza_item(name, base_price, category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar pizza"
        )
    return {"success": True, "message": "Pizza criada com sucesso"}

@router.patch("/items/price")
def update_item_price(item_id: str, price: float, catalog_context: Optional[CatalogContext] = None):
    """Atualiza preço de um item"""
    success = catalog_service.update_item_price(item_id, price, catalog_context)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao atualizar preço do item"
        )
    return {"success": True, "message": "Preço atualizado com sucesso"}

@router.patch("/options/price")
def update_option_price(option_id: str, price: float, 
                       parent_customization_option_id: Optional[str] = None,
                       catalog_context: Optional[CatalogContext] = None):
    """Atualiza preço de um complemento"""
    success = catalog_service.update_option_price(
        option_id, price, parent_customization_option_id, catalog_context
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao atualizar preço do complemento"
        )
    return {"success": True, "message": "Preço do complemento atualizado com sucesso"}

@router.patch("/items/status")
def update_item_status(item_id: str, status: ItemStatus, 
                      catalog_context: Optional[CatalogContext] = None):
    """Atualiza status de um item"""
    success = catalog_service.update_item_status(item_id, status, catalog_context)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao atualizar status do item"
        )
    return {"success": True, "message": "Status do item atualizado com sucesso"}

@router.patch("/options/status")
def update_option_status(option_id: str, status: ItemStatus,
                        parent_customization_option_id: Optional[str] = None,
                        catalog_context: Optional[CatalogContext] = None):
    """Atualiza status de um complemento"""
    success = catalog_service.update_option_status(
        option_id, status, parent_customization_option_id, catalog_context
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao atualizar status do complemento"
        )
    return {"success": True, "message": "Status do complemento atualizado com sucesso"}

@router.post("/image/upload")
def upload_image(file: UploadFile = File(...)):
    """Faz upload de uma imagem"""
    # Salva arquivo temporariamente
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
        content = file.file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        image_id = catalog_service.upload_image(tmp_path)
        if not image_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao fazer upload da imagem"
            )
        return {"success": True, "image_id": image_id}
    finally:
        os.unlink(tmp_path)