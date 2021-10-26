from uuid import uuid4
from flask import *
from blockchain import Blockchain
from waitress import serve
import logging
import sys

# instantiate our Node
app = Flask(__name__)

@app.route('/id', methods=['GET'])
def id():
    response = {
        'node_id': blockchain.node_id
    }

    return jsonify(response), 200

@app.route('/mine', methods=['GET'])
def mine():
    # we run the proof of work algorithm to get the next nonce
    block = blockchain.proof_of_work()

    response = {
        'message': 'new block forged',
        'block #': block['block']['#'],
        'difficulty': block['block']['difficulty'],
        'node_id': blockchain.node_id
    }

    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    nodes = request.get_json().get('nodes')

    if nodes is None or len(nodes) == 0:
        message = 'all available nodes'
    else:
        for node in nodes:
            blockchain.register_node(node)
        message = 'new nodes added'

    response = {
        'message': message,
        'all_nodes': list(blockchain.nodes.keys()),
        'node_id': blockchain.node_id
    }

    return jsonify(response), 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        message = 'our chain and pending transactions have been replaced'
    else:
        message = 'our chain is authoritative'

    response = {
            'message': message,
            'node_id': blockchain.node_id
        }

    return jsonify(response), 200

@app.route('/difficulty/update', methods=['GET'])
def update_difficulty():
    difficulty = request.args.get('difficulty')

    # if difficulty is supplied, update the node's difficulty
    # otherwise, return current difficulty
    if difficulty:
        difficulty_int = int(difficulty)
        if difficulty_int >= 1 and difficulty_int <= 5:
            blockchain.difficulty = difficulty_int
            message = 'difficulty has been updated'
        else:
            message = 'difficulty must be between 1 and 5'
    else:
        message = 'current difficulty'

    response = {
        'message': message,
        'difficulty': blockchain.difficulty,
        'node_id': blockchain.node_id
    }

    return jsonify(response), 200

@app.route('/difficulty/broadcast', methods=['GET'])
def broadcast_difficulty():
    difficulty = int(request.args.get('difficulty'))

    blockchain.broadcast_difficulty(difficulty)

    response = {
        'message': 'difficulty has been broadcasted to the network',
        'difficulty': difficulty,
        'node_id': blockchain.node_id
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
        'node_id': blockchain.node_id
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
        'message': 'transaction has been broadcasted to the network and will be added to the next block after validation',
        'transaction': transaction,
        'node_id': blockchain.node_id
        }

    return jsonify(response), 200

@app.route('/transactions/pending', methods=['GET'])
def pending_transactions():
    response = {
        'message': 'pending transactions',
        'pending_transactions': blockchain.pending_transactions,
        'node_id': blockchain.node_id
        }

    return jsonify(response), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'node_id': blockchain.node_id,
        'length': len(blockchain.chain),
        'effort': blockchain.effort
    }

    return jsonify(response), 200

@app.route('/utxo', methods=['GET'])
def utxo():
    response = {
        'balances': Blockchain.utxo(blockchain.chain),
        'node_id': blockchain.node_id
    }

    return jsonify(response), 200

@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')

  return response

if __name__ == '__main__':
    # if no port number is not provided
    if(len(sys.argv) < 2):
        port = 5000
    else:
        port = sys.argv[1]

    # if no node id is not provided
    if(len(sys.argv) < 3):
        node_id = str(uuid4()).replace('-', '')
    else:
        node_id = sys.argv[2]

    # instantiate the Blockchain
    blockchain = Blockchain(node_id=node_id, difficulty=3)

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.DEBUG)
    
    serve(app, host="0.0.0.0", port=port)
