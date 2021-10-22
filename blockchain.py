import hashlib
import json
from time import time
from urllib.parse import urlparse
import requests
import random

class Blockchain(object):
    def __init__(self, node_id):
        # the id of the node
        self.node_id = node_id
        # the dictionary of pending transactions
        self.current_transactions = []
        # the list of blocks
        self.chain = []
        # the next block to be forged but not yet finalized
        self.tentative_block = {}
        # the set of negbouring nodes
        self.nodes = set()

        # create the genesis block
        self.proof_of_work(previous_hash='0000')

    def new_block(self, nonce):
        """
        create a new block in the blockchain
        :param nonce: <int> the nonce given by the proof of work algorithm
        :return: <dict> new vlock
        """

        # set the nonce given by the proof of work algorithm
        self.tentative_block['block']['nonce'] = nonce
        # hash the new block
        self.tentative_block['hash'] = Blockchain.hash(self.tentative_block['block'])

        # add to the chain
        self.chain.append(self.tentative_block)

        # reset the current list of transactions
        self.current_transactions = []
        # reset the next block to be forged
        self.tentative_block = {}        

        # return the newly-created block
        return self.last_block

    def get_valid_transactions(self):
        """
        after each transaction, all accounts should have non-negative balances
        otherwise, reject the transction
        :return: <dict> a dict of valid transactions
        """
        valid_transactions = []

        for transaction in self.current_transactions:
            new_block = {
                'block': {
                    'transactions': valid_transactions + [transaction]
                }
            }
            balances = Blockchain.utxo(self.chain + [new_block])
            del balances['0']
            if all(value >= 0 for value in balances.values()):
                valid_transactions.append(transaction)
        
        return valid_transactions

    def proof_of_work(self, previous_hash=None):
        """
        simple proof of work algorithm:
         - find a number nonce such that hash(block(nonce)) contains several leading zeros
        :return: <dict> a dict of the newly minted block 
        """
        # validate transactions
        valid_transactions = self.get_valid_transactions()

        # block reward
        # will become finalized if the block is properly appended to the chain
        reward = {
            'sender': '0',
            'recipient': self.node_id,
            'amount': 1
        }

        self.tentative_block = {
            'block': {
                'index': len(self.chain) + 1,
                'timestamp': time(),
                # block reward appended to the current transaction list
                'transactions': valid_transactions + [reward],
                'nonce': 0,
                'previous_hash': previous_hash or self.last_block['hash']
            },
            'hash': ''
        }
        
        # find the nonce such that hash(block(nonce)) contains several leading zeros
        nonce = random.randint(0, 2147483647)
        while Blockchain.valid_proof(self.tentative_block, nonce) is False:
            nonce += 1

        # after finding the solution, add the block to chain
        block = self.new_block(nonce)

        return block

    def register_node(self, address):
        """
        add a new node to the list of nodes
        :param address: <str> address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def resolve_conflicts(self):
        """
        the consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """

        new_chain = None

        # we're only looking for chains longer than ours
        max_length = len(self.chain)

        # grab and verify the chains from all the nodes in our network
        for node in self.nodes:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and Blockchain.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            self.current_transactions = []
            return True

        return False

    def new_transaction(self, sender, recipient, amount):
        """
        creates a new transaction to go into the next mined block
        :param sender: <str> address of the Sender
        :param recipient: <str> address of the recipient
        :param amount: <float> amount
        :return: <int> the index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.current_transactions[-1]
    
    def broadcast_transaction(self, sender, recipient, amount):
        for node in self.nodes:
            response = requests.post(f'http://{node}/transactions/new', json={'sender': sender, 'recipient': recipient, 'amount': amount})

        return {'sender': sender, 'recipient': recipient, 'amount': amount}
    
    @staticmethod
    def utxo(chain):
        """
        calculate balance for each address from transaction history
        :return: <dict> unspent transaction output
        """
        balances = {}

        for block in chain:
            for transaction in block['block']['transactions']:
                # if address is already there, add the amount of the original balance
                # else, create new entry and record the amount
                # for recipient:
                if transaction['recipient'] in balances.keys():
                    balances[transaction['recipient']] += transaction['amount']
                else:
                    balances[transaction['recipient']] = transaction['amount']
                
                # for sender:
                if transaction['sender'] in balances.keys():
                    balances[transaction['sender']] -= transaction['amount']
                else:
                    balances[transaction['sender']] = -transaction['amount']
        
        for key in balances.keys():
            balances[key] = round(balances[key], 4)
        
        return balances

    @staticmethod
    def starts_with_zeros(string):
        difficulty = 3
        return string[:difficulty] == '0' * difficulty

    @staticmethod
    def hash(block_content):
        """
        creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # the dictionary must be ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block_content, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @staticmethod
    def valid_proof(block, nonce):
        """
        validates the nonce: does hash(last_nonce, nonce) start with several leading zeroes?
        :param last_nonce: <dict> a block
        :param nonce: <int> tentative nonce
        :return: <bool> True if correct, False if not.
        """
        block_copy = block.copy()
        block_copy['block']['nonce'] = nonce
        guess_hash = Blockchain.hash(block_copy['block'])
        return Blockchain.starts_with_zeros(guess_hash)
    
    @staticmethod
    def valid_chain(chain):
        """
        determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        # start from the 1st block
        current_index = 0

        while current_index < len(chain):
            block = chain[current_index]

            # Check that the hash of the block is correct
            if block['hash'] != Blockchain.hash(block['block']):
                return False

            # Check that the Proof of Work is correct block['hash'][:4] != '0000'
            if not Blockchain.starts_with_zeros(block['hash']):
                return False

            # move on to the next block
            current_index += 1

        return True

    @property
    def last_block(self):
        return self.chain[-1]