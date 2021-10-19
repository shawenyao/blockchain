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
        'message': 'New block forged',
        'index': block['block']['index'],
        'transactions': block['block']['transactions'],
        'nonce': block['block']['nonce'],
        'previous_hash': block['block']['previous_hash'],
        'hash': block['hash']
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return 'Error: Please supply a valid list of nodes', 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain has been replaced'
        }
    else:
        response = {
            'message': 'Our chain is authoritative'
        }

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

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
        'balances': blockchain.utxo(),
        'node_identifier': blockchain.node_identifier
    }
    return jsonify(response), 200

if __name__ == '__main__':
    if(len(sys.argv) == 1):
        port = 5000
    else:
        port = sys.argv[1]

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.DEBUG)
    
    serve(app, host="0.0.0.0", port=port)
