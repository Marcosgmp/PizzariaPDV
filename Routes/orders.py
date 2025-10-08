# routes/orders.py
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
import logging
import re
from typing import List, Dict

from Database.db import SessionLocal
from Models.orders import OrderStatus
from Models.products import Product
from Models.customers import Customer
from Services.orders import (
    create_order,
    update_order_status,
    get_order_with_details,
    get_active_orders,
    cancel_order
)

logger = logging.getLogger(__name__)
orders_bp = Blueprint('orders', __name__)

# Validadores
def validate_phone(phone: str) -> bool:
    """Valida formato de telefone (11 99999-9999 ou 11999999999)"""
    if not phone:  # Telefone é opcional para pedidos na loja
        return True
    pattern = r'^(\d{2}\s?\d{4,5}\s?\d{4})$'
    return bool(re.match(pattern, phone))

def validate_order_data(data: Dict, from_whatsapp: bool = False) -> List[str]:
    """Valida dados do pedido vindo do frontend"""
    errors = []
    
    # Para WhatsApp: cliente é obrigatório
    if from_whatsapp and not data.get('customer'):
        errors.append("Dados do cliente são obrigatórios para pedidos via WhatsApp")
    
    if data.get('customer'):
        customer = data['customer']
        if not customer.get('name') or len(customer['name'].strip()) < 2:
            errors.append("Nome do cliente é obrigatório (mínimo 2 caracteres)")
        
        # Telefone é obrigatório apenas para WhatsApp
        if from_whatsapp and not customer.get('phone'):
            errors.append("Telefone do cliente é obrigatório para pedidos via WhatsApp")
        elif customer.get('phone') and not validate_phone(customer['phone']):
            errors.append("Telefone inválido. Formato: 11 99999-9999")
    
    if not data.get('items') or len(data['items']) == 0:
        errors.append("Pelo menos um item é obrigatório no pedido")
    else:
        for i, item in enumerate(data['items']):
            if not item.get('product_id'):
                errors.append(f"Item {i+1}: product_id é obrigatório")
            if not item.get('quantity') or item['quantity'] < 1:
                errors.append(f"Item {i+1}: quantidade deve ser pelo menos 1")
    
    if not data.get('payment_method'):
        errors.append("Método de pagamento é obrigatório")
    elif data['payment_method'] not in ['DINHEIRO', 'CARTAO_CREDITO', 'CARTAO_DEBITO', 'PIX']:
        errors.append("Método de pagamento inválido")
    
    return errors

def get_or_create_customer(db: Session, customer_data: Dict, from_whatsapp: bool) -> int:
    """Busca ou cria cliente normal"""
    phone = customer_data['phone'].replace(' ', '') if customer_data.get('phone') else None
    
    if phone:
        existing_customer = db.query(Customer).filter(Customer.phone == phone).first()
        if existing_customer:
            # Atualiza dados se necessário
            if existing_customer.name_customers != customer_data['name']:
                existing_customer.name_customers = customer_data['name']
                db.commit()
            return existing_customer.id_customer
    
    # Cria novo cliente
    new_customer = Customer(
        name_customers=customer_data['name'],
        phone=phone,
        address=customer_data.get('address', 'Endereço não informado'),
        latitude=customer_data.get('latitude'),
        longitude=customer_data.get('longitude')
    )
    db.add(new_customer)
    db.flush()
    return new_customer.id_customer

def get_or_create_counter_customer(db: Session) -> int:
    """Busca ou cria cliente 'Balcão' para pedidos presenciais"""
    counter_customer = db.query(Customer).filter(
        Customer.phone == '00000000000'
    ).first()
    
    if counter_customer:
        return counter_customer.id_customer
    
    # Cria cliente balcão
    new_customer = Customer(
        name_customers="Cliente Balcão",
        phone="00000000000",
        address="Consumo no local",
        loyalty_points=0
    )
    db.add(new_customer)
    db.flush()
    return new_customer.id_customer

@orders_bp.route('/orders', methods=['POST'])
def create_order_route():
    """
    Cria um novo pedido - pode ser via WhatsApp ou na loja
    Query parameter: ?source=whatsapp ou ?source=store
    """
    try:
        data = request.json
        source = request.args.get('source', 'store')  # Default: pedido na loja
        from_whatsapp = (source.lower() == 'whatsapp')
        
        db = SessionLocal()
        
        # Validação conforme a origem
        validation_errors = validate_order_data(data, from_whatsapp)
        if validation_errors:
            return jsonify({"error": "Dados inválidos", "details": validation_errors}), 400
        
        customer_id = None
        
        # Processamento do cliente
        if data.get('customer'):
            customer_id = get_or_create_customer(db, data['customer'], from_whatsapp)
        elif not from_whatsapp:
            # Para pedidos na loja sem dados de cliente, usa cliente "Balcão"
            customer_id = get_or_create_counter_customer(db)
        
        # Prepara itens para o service
        order_items = []
        for item in data['items']:
            # Busca preço do produto no banco
            product = db.query(Product).filter(Product.id_product == item['product_id']).first()
            if not product:
                return jsonify({"error": f"Produto ID {item['product_id']} não encontrado"}), 404
            
            order_items.append({
                'id_product': item['product_id'],
                'quantity': item['quantity'],
                'note': item.get('note', ''),
                'price': str(product.price),
                'alert': item.get('alert', False)
            })
        
        # Cria pedido usando o service
        order = create_order(
            db=db,
            customer_id=customer_id,
            items=order_items,
            payment_method=data['payment_method']
        )
        
        response_data = {
            "success": True,
            "message": "Pedido criado com sucesso",
            "order_id": order.id_order,
            "total": float(order.total),
            "status": order.status_order.value,
            "source": source
        }
        
        if customer_id:
            response_data["customer_id"] = customer_id
        
        return jsonify(response_data), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao criar pedido: {e}")
        return jsonify({"error": "Erro interno ao criar pedido"}), 500
    finally:
        db.close()

@orders_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order_route(order_id):
    """
    Obtém um pedido específico com todos os detalhes
    """
    try:
        db = SessionLocal()
        order = get_order_with_details(db, order_id)
        
        if not order:
            return jsonify({"error": "Pedido não encontrado"}), 404
        
        # Formata resposta para o frontend
        response = {
            "id": order.id_order,
            "total": float(order.total),
            "status": order.status_order.value,
            "status_display": order.status_order.value.capitalize(),
            "payment_method": order.payment_method,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [{
                "id": item.id_item,
                "product": {
                    "id": item.product.id_product,
                    "name": item.product.name_product,
                    "price": float(item.product.price) if item.product.price else 0.0
                },
                "quantity": item.quantity,
                "note": item.note,
                "subtotal": float(item.unit_price * item.quantity) if item.unit_price else 0.0
            } for item in order.items],
            "payment": {
                "status": order.payments.status_payments.value if order.payments else None,
                "type": order.payments.type_payment if order.payments else None
            } if order.payments else None
        }
        
        # Adiciona dados do cliente se existir e não for balcão
        if order.customer and order.customer.phone != '00000000000':
            response["customer"] = {
                "id": order.customer.id_customer,
                "name": order.customer.name_customers,
                "phone": order.customer.phone,
                "address": order.customer.address
            }
        
        # Adiciona dados do entregador se existir
        if order.driver:
            response["driver"] = {
                "id": order.driver.id_driver,
                "name": order.driver.name_driver,
                "phone": order.driver.phone
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Erro ao buscar pedido {order_id}: {e}")
        return jsonify({"error": "Erro interno ao buscar pedido"}), 500
    finally:
        db.close()

@orders_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status_route(order_id):
    """
    Atualiza status do pedido
    """
    try:
        data = request.json
        db = SessionLocal()
        
        if not data.get('status'):
            return jsonify({"error": "status é obrigatório"}), 400
        
        # Mapeia status do frontend para enum
        status_mapping = {
            'recebido': OrderStatus.RECEBIDO,
            'preparando': OrderStatus.PREPARANDO,
            'a_caminho': OrderStatus.A_CAMINHO,
            'entregue': OrderStatus.ENTREGUE,
            'cancelado': OrderStatus.CANCELADO
        }
        
        status_lower = data['status'].lower()
        if status_lower not in status_mapping:
            return jsonify({"error": f"Status inválido. Válidos: {list(status_mapping.keys())}"}), 400
        
        order = update_order_status(
            db=db,
            order_id=order_id,
            new_status=status_mapping[status_lower],
            alert_message=data.get('alert_message')
        )
        
        return jsonify({
            "success": True,
            "message": "Status atualizado com sucesso",
            "order": {
                "id": order.id_order,
                "status": order.status_order.value,
                "status_display": order.status_order.value.capitalize()
            }
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao atualizar status do pedido {order_id}: {e}")
        return jsonify({"error": "Erro interno ao atualizar status"}), 500
    finally:
        db.close()

@orders_bp.route('/orders/active', methods=['GET'])
def get_active_orders_route():
    """
    Retorna pedidos ativos para o dashboard do frontend
    """
    try:
        db = SessionLocal()
        orders = get_active_orders(db)
        
        # Formata para o frontend
        orders_data = []
        for order in orders:
            order_data = {
                "id": order.id_order,
                "total": float(order.total),
                "status": order.status_order.value,
                "status_display": order.status_order.value.capitalize(),
                "payment_method": order.payment_method,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "items_count": len(order.items),
                "items_preview": [{
                    "name": item.product.name_product if item.product else "Produto não encontrado",
                    "quantity": item.quantity
                } for item in order.items[:2]]  # Primeiros 2 itens apenas para preview
            }
            
            # Adiciona nome do cliente se não for balcão
            if order.customer and order.customer.phone != '00000000000':
                order_data["customer_name"] = order.customer.name_customers
                order_data["customer_phone"] = order.customer.phone
            
            orders_data.append(order_data)
        
        return jsonify(orders_data)
        
    except Exception as e:
        logger.error(f"Erro ao buscar pedidos ativos: {e}")
        return jsonify({"error": "Erro interno ao buscar pedidos ativos"}), 500
    finally:
        db.close()

@orders_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
def cancel_order_route(order_id):
    """
    Cancela um pedido
    """
    try:
        data = request.json or {}
        db = SessionLocal()
        
        order = cancel_order(
            db=db,
            order_id=order_id,
            reason=data.get('reason', 'Solicitado pelo cliente')
        )
        
        return jsonify({
            "success": True,
            "message": "Pedido cancelado com sucesso",
            "order": {
                "id": order.id_order,
                "status": order.status_order.value,
                "status_display": order.status_order.value.capitalize()
            }
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao cancelar pedido {order_id}: {e}")
        return jsonify({"error": "Erro interno ao cancelar pedido"}), 500
    finally:
        db.close()

@orders_bp.route('/orders/status/<status>', methods=['GET'])
def get_orders_by_status_route(status):
    """
    Obtém pedidos por status
    """
    try:
        db = SessionLocal()
        
        # Mapeia status para enum
        status_mapping = {
            'recebido': OrderStatus.RECEBIDO,
            'preparando': OrderStatus.PREPARANDO,
            'a_caminho': OrderStatus.A_CAMINHO,
            'entregue': OrderStatus.ENTREGUE,
            'cancelado': OrderStatus.CANCELADO
        }
        
        status_lower = status.lower()
        if status_lower not in status_mapping:
            return jsonify({"error": f"Status inválido. Válidos: {list(status_mapping.keys())}"}), 400
        
        # TODO: Implementar get_orders_by_status no service
        orders = db.query(Order).filter(
            Order.status_order == status_mapping[status_lower]
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in orders:
            order_data = {
                "id": order.id_order,
                "total": float(order.total),
                "status": order.status_order.value,
                "payment_method": order.payment_method,
                "created_at": order.created_at.isoformat() if order.created_at else None
            }
            
            if order.customer and order.customer.phone != '00000000000':
                order_data["customer_name"] = order.customer.name_customers
            
            orders_data.append(order_data)
        
        return jsonify(orders_data)
        
    except Exception as e:
        logger.error(f"Erro ao buscar pedidos por status {status}: {e}")
        return jsonify({"error": "Erro interno ao buscar pedidos"}), 500
    finally:
        db.close()

@orders_bp.route('/orders/customer/<int:customer_id>', methods=['GET'])
def get_orders_by_customer_route(customer_id):
    """
    Obtém todos os pedidos de um cliente
    """
    try:
        db = SessionLocal()
        
        # TODO: Implementar get_orders_by_customer no service
        orders = db.query(Order).filter(
            Order.id_customer == customer_id
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in orders:
            orders_data.append({
                "id": order.id_order,
                "total": float(order.total),
                "status": order.status_order.value,
                "payment_method": order.payment_method,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "items_count": len(order.items)
            })
        
        return jsonify(orders_data)
        
    except Exception as e:
        logger.error(f"Erro ao buscar pedidos do cliente {customer_id}: {e}")
        return jsonify({"error": "Erro interno ao buscar pedidos"}), 500
    finally:
        db.close()