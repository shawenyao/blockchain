from uuid import uuid4
from flask import *
from blockchain import Blockchain
from waitress import serve
import logging
import sys

# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain(node_identifier)

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next nonce...
    block = blockchain.proof_of_work()

    response = {
        'message': 'new block forged',
        'index': block['block']['index'],
        'node_identifier': blockchain.node_identifier
    }

    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    nodes = request.get_json().get('nodes')

    if nodes is None or len(nodes) == 0:
        response = {
            'message': 'all available nodes',
            'all_nodes': list(blockchain.nodes),
            'node_identifier': blockchain.node_identifier
        }
    else:
        for node in nodes:
            blockchain.register_node(node)
        response = {
            'message': 'new nodes added',
            'all_nodes': list(blockchain.nodes),
            'node_identifier': blockchain.node_identifier
        }

    return jsonify(response), 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'our chain has been replaced',
            'node_identifier': blockchain.node_identifier
        }
    else:
        response = {
            'message': 'our chain is authoritative',
            'node_identifier': blockchain.node_identifier
        }

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # create a new transaction
    transaction = blockchain.new_transaction(values['sender'], values['recipient'], float(values['amount']))

    response = {
        'message': 'transaction will be added to the next block after validation',
        'transaction': transaction,
        'node_identifier': blockchain.node_identifier
        }

    return jsonify(response), 200

@app.route('/transactions/broadcast', methods=['POST'])
def broadcast_transaction():
    values = request.get_json()

    # check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # broadcast a new transaction
    transaction = blockchain.broadcast_transaction(values['sender'], values['recipient'], float(values['amount']))

    response = {
        'message': 'transaction has been broadcasted to all nodes and will be added to the next block after validation',
        'transaction': transaction,
        'node_identifier': blockchain.node_identifier
        }

    return jsonify(response), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'node_identifier': blockchain.node_identifier,
        'length': len(blockchain.chain),
    }

    return jsonify(response), 200

@app.route('/utxo', methods=['GET'])
def utxo():
    response = {
        'balances': Blockchain.utxo(blockchain.chain),
        'node_identifier': blockchain.node_identifier
    }

    return jsonify(response), 200

@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')

  return response

if __name__ == '__main__':
    if(len(sys.argv) == 1):
        port = 5000
    else:
        port = sys.argv[1]

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.DEBUG)
    
    serve(app, host="0.0.0.0", port=port)
