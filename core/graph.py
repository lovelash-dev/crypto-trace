from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from core.fetcher import BlockchainFetcher

@dataclass
class Edge:
    tx_hash: str
    from_address: str
    to_address: str
    amount_wei: int
    gas_fee_wei: int
    stolen_flow_wei: int
    block_number: int
    @property
    def amount_eth(self): return BlockchainFetcher.wei_to_eth(self.amount_wei)
    @property
    def gas_fee_eth(self): return BlockchainFetcher.wei_to_eth(self.gas_fee_wei)

class Node:
    def __init__(self, address: str, depth: int = 0, initial_stolen_flow_wei: int = 0):
        self.address = address.lower()
        self.depth = depth
        self.stolen_flow_wei = initial_stolen_flow_wei
        self.edges: List[Edge] = []
        self.children: List["Node"] = []
    @property
    def stolen_flow(self): return BlockchainFetcher.wei_to_eth(self.stolen_flow_wei)
    @property
    def is_endpoint(self): return len(self.children) == 0

class TransactionGraph:
    def __init__(self, fetcher: BlockchainFetcher, max_depth: int = 7, max_transactions: int = 100):
        self.fetcher, self.max_depth, self.max_transactions = fetcher, max_depth, max_transactions
        self.root: Optional[Node] = None
        self.visited_txs: Set[str] = set()
        self.all_nodes: Dict[str, Node] = {}

    def build_from_origin(self, origin_data: Dict) -> Node:
        amount = int(origin_data["value_wei"])
        address = origin_data["to_address"]
        self.root = Node(address, 0, amount)
        self.all_nodes[address] = self.root
        self.visited_txs.add(origin_data["tx_hash"])
        self._trace_recursive(self.root)
        return self.root

    def _trace_recursive(self, node: Node, path: Optional[Set[str]] = None):
        if node.depth >= self.max_depth: return
        path = path or set()
        if node.address in path: return
        path = path | {node.address}
        txs = self.fetcher.get_outgoing_transactions(node.address, self.max_transactions)
        if not txs: return
        total = sum(int(tx["value_wei"]) for tx in txs)
        gas_total = sum(int(tx["gas_price_wei"])*int(tx["gas_used"]) for tx in txs)
        available = max(0, node.stolen_flow_wei-gas_total)
        if total == 0 or available == 0: return
        allocated_total = 0
        for index, tx in enumerate(txs):
            tx_hash = tx["tx_hash"]
            if tx_hash in self.visited_txs: continue
            self.visited_txs.add(tx_hash)
            allocation = (available-allocated_total if index == len(txs)-1
                          else available*int(tx["value_wei"])//total)
            allocated_total += allocation
            target = tx["to_address"]
            edge = Edge(tx_hash,node.address,target,int(tx["value_wei"]),
                int(tx["gas_price_wei"])*int(tx["gas_used"]),allocation,int(tx["block_number"]))
            node.edges.append(edge)
            if target in self.all_nodes:
                child = self.all_nodes[target]
                child.stolen_flow_wei += allocation
            else:
                child = Node(target,node.depth+1,allocation)
                self.all_nodes[target] = child
            node.children.append(child)
            self._trace_recursive(child,path)

    def get_endpoints(self):
        return [node for node in self.all_nodes.values() if node.is_endpoint]
