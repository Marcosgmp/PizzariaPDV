# services/payments.py
from sqlalchemy.orm import Session
from Models.payments import Payment, PaymentStatus
from Models.orders import Order, OrderStatus
from Models.cash_alerts import CashAlert
from decimal import Decimal
from typing import Optional
import logging
import requests

# Configurar logging
logger = logging.getLogger(__name__)

def create_payment(db: Session, order_id: int, payment_type: str, amount: Decimal, change_amount: Decimal = Decimal('0.00'), notify: bool = True) -> Payment:
    """
    Cria um pagamento para um pedido.
    
    Args:
        db: Sessão do banco de dados
        order_id: ID do pedido
        payment_type: Tipo de pagamento (dinheiro, cartão, pix, etc.)
        amount: Valor do pagamento
        change_amount: Valor do troco (para pagamento em dinheiro)
        notify: Se deve enviar notificações
    
    Returns:
        Objeto Payment criado
    """
    try:
        # Verifica se o pedido existe
        order = db.query(Order).filter(Order.id_order == order_id).first()
        if not order:
            raise ValueError(f"Pedido {order_id} não encontrado")
        
        # Verifica se já existe pagamento para este pedido
        existing_payment = db.query(Payment).filter(Payment.id_order == order_id).first()
        if existing_payment:
            raise ValueError(f"Já existe um pagamento para o pedido {order_id}")
        
        # Valida se o valor do pagamento é suficiente
        if amount < order.total:
            raise ValueError(f"Valor insuficiente. Total: R$ {order.total}, Pago: R$ {amount}")
        
        # Cria o pagamento
        payment = Payment(
            id_order=order_id,
            type_payment=payment_type,
            amount=amount,
            change_amount=change_amount,
            status_payments=PaymentStatus.PENDENTE
        )
        db.add(payment)
        db.flush()
        
        # Se pagamento for confirmado automaticamente (cartão, pix)
        if payment_type in ['CARTAO_CREDITO', 'CARTAO_DEBITO', 'PIX']:
            payment.status_payments = PaymentStatus.CONFIRMADO
            order.status_order = OrderStatus.PREPARANDO
            
            # Cria alerta de pagamento confirmado
            create_payment_alert(
                db, 
                order_id, 
                f"PAGAMENTO CONFIRMADO: {payment_type} - R$ {amount}"
            )
        
        # Pagamento em dinheiro - precisa de confirmação
        elif payment_type == 'DINHEIRO':
            if amount > order.total:
                # Cria alerta para troco
                create_payment_alert(
                    db,
                    order_id,
                    f"PAGAMENTO DINHEIRO: R$ {amount} - TROCO: R$ {change_amount}"
                )
            payment.status_payments = PaymentStatus.CONFIRMADO
            order.status_order = OrderStatus.PREPARANDO
        
        db.commit()
        db.refresh(payment)
        
        # Integração com sistemas externos
        if payment.status_payments == PaymentStatus.CONFIRMADO:
            try:
                # Gerar NFC-e (implementar integração com ACBr)
                generate_nfe(db, order_id, amount)
                
                # Enviar notificação
                if notify:
                    send_payment_notification(db, order_id, payment_type, amount)
                    
            except Exception as e:
                logger.error(f"Erro na integração pós-pagamento: {e}")
                # Não falha a operação principal por erro na integração
        
        return payment
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar pagamento: {e}")
        raise

def update_payment_status(db: Session, payment_id: int, new_status: PaymentStatus) -> Payment:
    """
    Atualiza o status do pagamento.
    
    Args:
        db: Sessão do banco de dados
        payment_id: ID do pagamento
        new_status: Novo status do pagamento
    
    Returns:
        Objeto Payment atualizado
    """
    try:
        payment = db.query(Payment).filter(Payment.id_payment == payment_id).first()
        if not payment:
            raise ValueError(f"Pagamento {payment_id} não encontrado")
        
        old_status = payment.status_payments
        payment.status_payments = new_status
        
        # Atualiza status do pedido baseado no pagamento
        order = db.query(Order).filter(Order.id_order == payment.id_order).first()
        if order:
            if new_status == PaymentStatus.CONFIRMADO:
                order.status_order = OrderStatus.PREPARANDO
            elif new_status == PaymentStatus.CANCELADO:
                order.status_order = OrderStatus.CANCELADO
                
                # Cria alerta de pagamento cancelado
                create_payment_alert(
                    db, 
                    payment.id_order, 
                    f"PAGAMENTO CANCELADO: {payment.type_payment} - R$ {payment.amount}"
                )
        
        db.commit()
        db.refresh(payment)
        
        logger.info(f"Pagamento {payment_id} atualizado: {old_status} -> {new_status}")
        return payment
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar status do pagamento: {e}")
        raise

def get_payment_by_order(db: Session, order_id: int) -> Optional[Payment]:
    """
    Retorna o pagamento associado a um pedido.
    
    Args:
        db: Sessão do banco de dados
        order_id: ID do pedido
    
    Returns:
        Objeto Payment ou None se não encontrado
    """
    return db.query(Payment).filter(Payment.id_order == order_id).first()

def cancel_payment(db: Session, payment_id: int) -> Payment:
    """
    Cancela um pagamento.
    
    Args:
        db: Sessão do banco de dados
        payment_id: ID do pagamento
    
    Returns:
        Objeto Payment cancelado
    """
    return update_payment_status(db, payment_id, PaymentStatus.CANCELADO)

def process_refund(db: Session, payment_id: int, refund_amount: Decimal = None) -> Payment:
    """
    Processa um reembolso para um pagamento.
    
    Args:
        db: Sessão do banco de dados
        payment_id: ID do pagamento
        refund_amount: Valor do reembolso (None para reembolso total)
    
    Returns:
        Objeto Payment atualizado
    """
    try:
        payment = db.query(Payment).filter(Payment.id_payment == payment_id).first()
        if not payment:
            raise ValueError(f"Pagamento {payment_id} não encontrado")
        
        if payment.status_payments != PaymentStatus.CONFIRMADO:
            raise ValueError("Apenas pagamentos confirmados podem ser reembolsados")
        
        # Define valor do reembolso (padrão: valor total)
        if refund_amount is None:
            refund_amount = payment.amount
        elif refund_amount > payment.amount:
            raise ValueError("Valor do reembolso não pode ser maior que o valor pago")
        
        # Marca como reembolsado
        payment.status_payments = PaymentStatus.REEMBOLSADO
        payment.refund_amount = refund_amount
        
        # Cria alerta de reembolso
        create_payment_alert(
            db, 
            payment.id_order, 
            f"REEMBOLSO PROCESSADO: R$ {refund_amount} - {payment.type_payment}"
        )
        
        db.commit()
        db.refresh(payment)
        
        # TODO: Integrar com gateway de pagamento para estornar valor
        
        return payment
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao processar reembolso: {e}")
        raise

def create_payment_alert(db: Session, order_id: int, message: str) -> CashAlert:
    """
    Cria um alerta relacionado a pagamento.
    
    Args:
        db: Sessão do banco de dados
        order_id: ID do pedido
        message: Mensagem do alerta
    
    Returns:
        Objeto CashAlert criado
    """
    alert = CashAlert(
        id_order=order_id,
        message_alert=message,
        alert_type="PAGAMENTO",
        status="ATIVO"
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

# Funções de integração (implementar conforme necessidade)
def generate_nfe(db: Session, order_id: int, amount: Decimal) -> bool:
    """
    Gera NFC-e através da integração com ACBr.
    Implementar de acordo com a biblioteca ACBr.
    """
    try:
        # TODO: Implementar integração com ACBr
        logger.info(f"NFC-e gerada para pedido {order_id} - Valor: R$ {amount}")
        return True
    except Exception as e:
        logger.error(f"Erro ao gerar NFC-e: {e}")
        return False

def send_payment_notification(db: Session, order_id: int, payment_type: str, amount: Decimal) -> bool:
    """
    Envia notificação de pagamento via WhatsApp/Telegram.
    Implementar de acordo com a API escolhida.
    """
    try:
        # TODO: Implementar integração com WhatsApp Business API ou Telegram
        order = db.query(Order).filter(Order.id_order == order_id).first()
        if order and order.customer:
            message = f"✅ Pagamento confirmado! Pedido #{order_id} - R$ {amount} - {payment_type}"
            logger.info(f"Notificação enviada: {message}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar notificação: {e}")
        return False

def get_payment_summary(db: Session, date_filter: str = None) -> dict:
    """
    Retorna resumo de pagamentos por tipo e status.
    
    Args:
        db: Sessão do banco de dados
        date_filter: Data para filtrar (formato YYYY-MM-DD)
    
    Returns:
        Dicionário com resumo de pagamentos
    """
    # TODO: Implementar lógica de resumo por data
    summary = {
        'total_recebido': Decimal('0.00'),
        'por_tipo': {},
        'por_status': {}
    }
    
    return summary