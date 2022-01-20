import hashlib
import json
import requests
import random
from pytz import timezone
from datetime import datetime
from urllib.parse import urlparse


class Blockchain(object):
    def __init__(self, node_id, difficulty):
        # the id of the node
        self.node_id = node_id
        # the dictionary of pending transactions
        self.pending_transactions = []
        # the list of blocks
        self.chain = []
        # the next block to be forged but not yet finalized
        self.tentative_block = {}
        # the set of all peer nodes
        self.nodes = {}
        # the difficulty of mining
        self.difficulty = difficulty
        # the effort it took to build the chain
        # e.g., a block with difficulty 2 takes 16 times the effort to build than a block with difficulty 1
        self.effort = 0

        # create the genesis block
        # where previous hash is hard-coded
        self.proof_of_work(previous_hash='[note: previous hash is not applicable in the case of genesis block]')

    def new_block(self, nonce, index_valid_transactions):
        """
        create a new block in the blockchain
        :param nonce: <int> the nonce given by the proof of work algorithm
        :return: <dict> the newly minted bvlock
        """

        # set the nonce given by the proof of work algorithm
        self.tentative_block['block']['nonce'] = nonce
        # hash the new block
        self.tentative_block['hash'] = Blockchain.hash(self.tentative_block['block'])

        # add to the chain
        self.chain.append(self.tentative_block)

        # increase effort of the chain
        self.effort += 16 ** (self.tentative_block['block']['difficulty']-1)

        # currently invalid (unprocessed) transactions becomes the new list of pending transactions
        self.pending_transactions = [transaction for (i, transaction) in enumerate(self.pending_transactions) if i not in index_valid_transactions]
        # reset the next block to be forged (not ncessary as it will be overwritten in the next call of proof_of_work)
        # self.tentative_block = {}

        # return the newly-created block
        return self.last_block

    def get_valid_transactions(self):
        """
        after each transaction, all accounts should have non-negative balances
        otherwise, reject the transction
        :return: <list> index of valid transactions
        """
        index_valid_transactions = []
        valid_transactions = []

        for i, transaction in enumerate(self.pending_transactions):
            new_block = {
                'block': {
                    'transactions': valid_transactions + [transaction]
                }
            }
            balances = Blockchain.utxo(self.chain + [new_block])
            del balances['0']
            if all(value >= 0 for value in balances.values()):
                index_valid_transactions.append(i)
                valid_transactions.append(transaction)
        
        return index_valid_transactions

    def proof_of_work(self, previous_hash=None):
        """
        simple proof of work algorithm:
         - find a number nonce such that hash(block(nonce)) contains several leading zeros
        :return: <dict> the newly minted block 
        """
        # validate transactions
        index_valid_transactions = self.get_valid_transactions()

        # block reward (aka coinbase)
        # will become finalized if the block is properly appended to the chain
        # if previous_hash is provided (i.e., genesis block), use hard-coded recipient
        reward = {
            'sender': '0',
            'recipient': 'satoshi' if previous_hash else self.node_id,
            'amount': 1
        }

        # new block for which nonce needs to be solved
        self.tentative_block = {
            'block': {
                '#': len(self.chain) + 1,
                'difficulty': self.difficulty,
                'nonce': 0,
                # if previous_hash is provided (i.e., genesis block), use hard-coded timestamp
                'timestamp': datetime(2009, 1, 3, 13, 15).strftime('%b %d, %Y %H:%M:%S %p ET')\
                     if previous_hash else datetime.now(timezone('US/Eastern')).strftime('%b %d, %Y %H:%M:%S %p ET'),
                # block reward appended to the current list of valid pending transactions
                'transactions': [self.pending_transactions[i] for i in index_valid_transactions] + [reward],
                'previous_hash': previous_hash or self.last_block['hash']
            },
            'hash': ''
        }
        
        # if previous_hash is provided (i.e., genesis block), use hard-coded nonce (pre-solved)
        if previous_hash:
            nonce = 1443031394
        else:
            # find the nonce such that hash(block(nonce)) contains the required number of leading zeros
            nonce = random.randint(0, 2147483647)
            while Blockchain.valid_proof(self.tentative_block, nonce, self.tentative_block['block']['difficulty']) is False:
                # next guess
                nonce += 1

        # after finding the solution, add the block to chain
        # the invalid transactions will back to pending state
        block = self.new_block(nonce, index_valid_transactions)

        return block

    def register_node(self, address):
        """
        add a new node to the list of nodes
        :param address: <str> address of node. Eg. 'http://192.168.0.5:5000'
        """

        new_node_address = urlparse(address).netloc
        
        # get node id from node address
        response = requests.get(f'http://{new_node_address}/id')

        # save to my node list
        if response.status_code == 200:
            self.nodes[response.json()['node_id']] = new_node_address

    def resolve_conflicts(self):
        """
        the consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network (as well as pending transactions)
        :return: <bool> True if our chain was replaced, False if not
        """

        authoritative_node = None
        new_chain = None

        # we're only looking for chains that are built with more effort than ours
        max_effort = self.effort

        # grab and verify the chains from all the nodes in our network
        for node in self.nodes.values():
            response_chain = requests.get(f'http://{node}/chain')
            if response_chain.status_code == 200:
                effort = response_chain.json()['effort']
                chain = response_chain.json()['chain']

                # check if the effort is greater and the chain is valid
                if effort > max_effort and Blockchain.valid_chain(chain):
                    authoritative_node = node
                    max_effort = effort
                    new_chain = chain

        # replace our chain if we discovered a new, valid chain that took more effort to build than ours
        if new_chain:
            self.chain = new_chain
            self.effort = max_effort

            # replace our pending transactions as well
            response_pending_transactions = requests.get(f'http://{authoritative_node}/transactions/pending')
            if response_pending_transactions.status_code == 200:
                self.pending_transactions = response_pending_transactions.json()['pending_transactions']
            
            return True

        return False

    def new_transaction(self, sender, recipient, amount):
        """
        create a new transaction to go into the next mined block
        :param sender: <str> node id of the sender
        :param recipient: <str> node id of the recipient
        :param amount: <float> amount
        :return: <dict> this transaction
        """
        self.pending_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        return self.pending_transactions[-1]
    
    def broadcast_transaction(self, sender, recipient, amount):
        for node in self.nodes.values():
            requests.post(f'http://{node}/transactions/new', json={'sender': sender, 'recipient': recipient, 'amount': amount})

        return {'sender': sender, 'recipient': recipient, 'amount': amount}
    
    def broadcast_difficulty(self, difficulty):
        for node in self.nodes.values():
            requests.get(f'http://{node}/difficulty/update?difficulty={difficulty}')
    
    @staticmethod
    def utxo(chain):
        """
        calculate balance for each node id from transaction history
        :return: <dict> unspent transaction output
        """
        balances = {}

        for block in chain:
            for transaction in block['block']['transactions']:
                # if node id is already there, adjust the original balance by the transaction amount
                # else, create new entry and record the amount
                # for recipient:
                balances[transaction['recipient']] = balances.get(transaction['recipient'], 0) + transaction['amount']
                # for sender:
                balances[transaction['sender']] = balances.get(transaction['sender'], 0) - transaction['amount']
        
        for key in balances.keys():
            # round the balance to 8 decimal places
            balances[key] = round(balances[key], 8)
        
        return balances

    @staticmethod
    def starts_with_zeros(string, difficulty):
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
    def valid_proof(block, nonce, difficulty):
        """
        validates the nonce: does hash(block(nonce)) start with several leading zeroes?
        :param last_nonce: <dict> a block
        :param nonce: <int> tentative nonce
        :return: <bool> True if correct, False if not.
        """
        block_copy = block.copy()
        block_copy['block']['nonce'] = nonce
        guess_hash = Blockchain.hash(block_copy['block'])
        return Blockchain.starts_with_zeros(guess_hash, difficulty)
    
    @staticmethod
    def oracle():
        """
        get btc to usd price from yahoo finance
        :return: <float>
        """
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        response = requests.get('http://query1.finance.yahoo.com/v6/finance/quote?region=US&lang=en&symbols=BTC-USD', headers=headers)

        if response.status_code == 200:
            btcprice = response.json()['quoteResponse']['result'][0]['regularMarketPrice']
        else:
            btcprice = None
        
        return btcprice

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

            # for every block after the 1st one, check if it's pointing to the previous hash
            if current_index > 0 and block['block']['previous_hash'] != chain[current_index-1]['hash']:
                return False

            # check that the hash of the block is correct
            if block['hash'] != Blockchain.hash(block['block']):
                return False

            # check that the proof of work is correct
            if not Blockchain.starts_with_zeros(block['hash'], block['block']['difficulty']):
                return False

            # (out-of-scope) also needs to check if all transactions are valid
            # including 1) the sender has sufficient funds and 2) the sender's identity (digital signature)

            # move on to the next block
            current_index += 1

        return True

    @property
    def last_block(self):
        return self.chain[-1]