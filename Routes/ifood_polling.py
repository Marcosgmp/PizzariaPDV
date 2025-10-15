from flask import Blueprint, request, jsonify
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ifood_services.polling import ifood_polling_service, PollingType

ifood_polling_bp = Blueprint('ifood_polling', __name__)

@ifood_polling_bp.route('/api/ifood/polling/start', methods=['POST'])
def start_polling():
    """Inicia o serviço de polling"""
    try:
        ifood_polling_service.start_polling()
        return jsonify({
            'status': 'success',
            'message': 'Polling iniciado',
            'data': ifood_polling_service.get_status()
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ifood_polling_bp.route('/api/ifood/polling/stop', methods=['POST'])
def stop_polling():
    """Para o serviço de polling"""
    try:
        ifood_polling_service.stop_polling()
        return jsonify({
            'status': 'success', 
            'message': 'Polling parado',
            'data': ifood_polling_service.get_status()
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ifood_polling_bp.route('/api/ifood/polling/status', methods=['GET'])
def get_polling_status():
    """Retorna status do polling"""
    try:
        return jsonify({
            'status': 'success',
            'data': ifood_polling_service.get_status()
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ifood_polling_bp.route('/api/ifood/polling/force', methods=['POST'])
def force_poll():
    """Força uma execução de polling"""
    try:
        poll_type = request.json.get('type', 'orders')
        
        try:
            poll_type_enum = PollingType(poll_type)
        except ValueError:
            return jsonify({
                'status': 'error', 
                'message': f'Tipo inválido: {poll_type}. Válidos: {[t.value for t in PollingType]}'
            }), 400
        
        result = ifood_polling_service.force_poll(poll_type_enum)
        
        return jsonify({
            'status': 'success' if result.success else 'error',
            'message': result.error or 'Polling executado',
            'data': {
                'type': result.type.value,
                'success': result.success,
                'items_processed': result.items_processed,
                'timestamp': result.timestamp.isoformat(),
                'error': result.error
            }
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ifood_polling_bp.route('/api/ifood/polling/config', methods=['PUT'])
def update_config():
    """Atualiza configuração de polling"""
    try:
        poll_type = request.json.get('type')
        config_updates = request.json.get('config', {})
        
        if not poll_type:
            return jsonify({'status': 'error', 'message': 'Tipo é obrigatório'}), 400
        
        try:
            poll_type_enum = PollingType(poll_type)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': f'Tipo inválido: {poll_type}'
            }), 400
        
        ifood_polling_service.update_config(poll_type_enum, **config_updates)
        
        return jsonify({
            'status': 'success',
            'message': 'Configuração atualizada',
            'data': ifood_polling_service.get_status()
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500