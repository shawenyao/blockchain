import hashlib
import json
from time import time
from urllib.parse import urlparse
import requests
import random

class Blockchain(object):
    def __init__(self, node_identifier):
        self.node_identifier = node_identifier
        self.current_transactions = []
        self.chain = []
        self.tentative_block = {}
        self.nodes = set()

        # Create the genesis block
        self.proof_of_work(previous_hash='0000')

    def utxo(self):
        """
        Calculate balance for each address from transaction history
        :return: <dict> unspent transaction output
        """
        balances = {}

        for block in self.chain:
            for transaction in block['transactions']:
                if transaction['recipient'] in balances.keys():
                    balances[transaction['recipient']] += transaction['amount']
                else:
                    balances[transaction['recipient']] = transaction['amount']
                
                if transaction['sender'] in balances.keys():
                    balances[transaction['sender']] -= transaction['amount']
                else:
                    balances[transaction['sender']] = -transaction['amount']
        
        return balances

    def new_block(self, nonce):
        """
        Create a new Block in the Blockchain
        :param nonce: <int> The nonce given by the nonce of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        # hash the new block
        self.tentative_block['nonce'] = nonce
        self.tentative_block['hash'] = self.hash(self.tentative_block)

        self.chain.append(self.tentative_block)

        # Reset the current list of transactions
        self.current_transactions = []
        self.tentative_block = {}        

        return self.last_block

    def proof_of_work(self, previous_hash=None):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where
         - p is the previous nonce, and p' is the new nonce
        :param last_nonce: <int>
        :return: <int>
        """

        # block reward
        reward = {
            'sender': '0',
            'recipient': self.node_identifier,
            'amount': 1
        }

        self.tentative_block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions.copy() + [reward],
            'nonce': 0,
            'previous_hash': previous_hash or self.last_block['hash'],
            'hash': ''
        }
        
        nonce = random.randint(0, 2147483647)
        while self.valid_proof(self.tentative_block, nonce) is False:
            nonce += 1

        block = self.new_block(nonce)

        return block

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        current_index = 0

        while current_index < len(chain):
            block = chain[current_index]
            # Check that the hash of the block is correct
            if block['hash'] != self.hash(block):
                return False

            # Check that the Proof of Work is correct block['hash'][:4] != '0000'
            if not self.leading_zeros(block['hash']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        block_copy = block.copy()

        # remove hash of the block to re-caculate the hash of the block
        block_copy['hash'] = ''
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1
    
    @staticmethod
    def valid_proof(block, nonce):
        """
        Validates the nonce: Does hash(last_nonce, nonce) contain 4 leading zeroes?
        :param last_nonce: <int> Previous nonce
        :param nonce: <int> Current nonce
        :return: <bool> True if correct, False if not.
        """
        block_copy = block.copy()
        block_copy['nonce'] = nonce
        guess_hash = Blockchain.hash(block_copy)
        return Blockchain.leading_zeros(guess_hash)
    
    @staticmethod
    def leading_zeros(string):
        return string[:4] == '0000'

    @property
    def last_block(self):
        return self.chain[-1]