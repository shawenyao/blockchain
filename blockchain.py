import hashlib
import json
from time import time
from urllib.parse import urlparse
import requests
import random

class Blockchain(object):
    def __init__(self, node_identifier):
        # the id of the node
        self.node_identifier = node_identifier
        # the dictionary of pending transactions
        self.current_transactions = []
        # the list of blockchain
        self.chain = []
        # the next block to be forged but not yet finalized
        self.tentative_block = {}
        # the set of negbouring nodes
        self.nodes = set()

        # Create the genesis block
        self.proof_of_work(previous_hash='0000')

    def utxo(self):
        """
        calculate balance for each address from transaction history
        :return: <dict> unspent transaction output
        """
        balances = {}

        for block in self.chain:
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
        
        return balances

    def new_block(self, nonce):
        """
        create a new block in the blockchain
        :param nonce: <int> the nonce given by the proof of work algorithm
        :return: <dict> new vlock
        """

        # set the nonce given by the proof of work algorithm
        self.tentative_block['block']['nonce'] = nonce
        # hash the new block
        self.tentative_block['hash'] = self.hash(self.tentative_block['block'])

        # add to the chain
        self.chain.append(self.tentative_block)

        # reset the current list of transactions
        self.current_transactions = []
        # reset the next block to be forged
        self.tentative_block = {}        

        # return the newly-created block
        return self.last_block

    def proof_of_work(self, previous_hash=None):
        """
        simple proof of work algorithm:
         - find a number nonce such that hash(block(nonce)) contains several leading zeros
        :param last_nonce: <int>
        :return: <int>
        """

        # block reward
        # will become finalized if the block is properly appended to the chain
        reward = {
            'sender': '0',
            'recipient': self.node_identifier,
            'amount': 1
        }

        self.tentative_block = {
            'block': {
                'index': len(self.chain) + 1,
                'timestamp': time(),
                # block reward appended to the current transaction list
                'transactions': self.current_transactions + [reward],
                'nonce': 0,
                'previous_hash': previous_hash or self.last_block['hash']
            },
            'hash': ''
        }
        
        # find the nonce such that hash(block(nonce)) contains several leading zeros
        nonce = random.randint(0, 2147483647)
        while self.valid_proof(self.tentative_block, nonce) is False:
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

    def valid_chain(self, chain):
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
            if block['hash'] != self.hash(block['block']):
                return False

            # Check that the Proof of Work is correct block['hash'][:4] != '0000'
            if not self.starts_with_zeros(block['hash']):
                return False

            # move on to the next block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        the consensus algorithm, it resolves conflicts
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
    def hash(block_content):
        """
        creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # the dictionary must be ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block_content, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def new_transaction(self, sender, recipient, amount):
        """
        creates a new transaction to go into the next mined block
        :param sender: <str> address of the Sender
        :param recipient: <str> address of the recipient
        :param amount: <int> amount
        :return: <int> the index of the Block that will hold this transaction
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
    def starts_with_zeros(string):
        return string[:4] == '0000'

    @property
    def last_block(self):
        return self.chain[-1]