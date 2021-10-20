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

    response = jsonify({
        'message': 'new block forged',
        'index': block['block']['index']
    })
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response, 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    nodes = request.get_json().get('nodes')

    if nodes is None or len(nodes) == 0:
        response = jsonify({
            'message': 'available nodes',
            'total_nodes': list(blockchain.nodes),
        })
    else:
        for node in nodes:
            blockchain.register_node(node)
        response = jsonify({
            'message': 'new nodes added',
            'total_nodes': list(blockchain.nodes),
        })
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response, 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = jsonify({
            'message': 'our chain has been replaced'
        })
    else:
        response = jsonify({
            'message': 'our chain is authoritative'
        })
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response, 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = jsonify({'message': f'transaction will be added to block {index}'})
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response, 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = jsonify({
        'chain': blockchain.chain,
        'node_identifier': blockchain.node_identifier,
        'length': len(blockchain.chain),
    })
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response, 200

@app.route('/utxo', methods=['GET'])
def utxo():
    response = jsonify({
        'balances': blockchain.utxo(),
        'node_identifier': blockchain.node_identifier
    })
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response, 200

if __name__ == '__main__':
    if(len(sys.argv) == 1):
        port = 5000
    else:
        port = sys.argv[1]

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.DEBUG)
    
    serve(app, host="0.0.0.0", port=port)
