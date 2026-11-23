from dataclasses import dataclass
from typing import Any, Dict
from core.graph import TransactionGraph

@dataclass
class ReconciliationReport:
    initial_stolen_amount: float
    tracked_stolen_flow: float
    total_gas_fees_eth: float
    unaccounted_amount: float
    is_fully_accounted: bool
    total_endpoints: int
    total_nodes_analyzed: int
    def to_dict(self) -> Dict[str, Any]:
        return {"initial_stolen_amount":self.initial_stolen_amount,
            "tracked_stolen_flow":self.tracked_stolen_flow,
            "total_gas_fees_eth":self.total_gas_fees_eth,
            "unaccounted_amount":self.unaccounted_amount,
            "is_fully_accounted":self.is_fully_accounted,
            "total_endpoints":self.total_endpoints,
            "total_nodes_analyzed":self.total_nodes_analyzed}

class FundReconciler:
    def __init__(self, origin_amount_wei: int):
        self.origin_amount_wei = int(origin_amount_wei)
    def analyze(self, graph: TransactionGraph) -> ReconciliationReport:
        endpoints = graph.get_endpoints()
        tracked = sum(node.stolen_flow_wei for node in endpoints)
        gas = sum(edge.gas_fee_wei for node in graph.all_nodes.values() for edge in node.edges)
        unaccounted = self.origin_amount_wei-tracked-gas
        to_eth = lambda value: value/10**18
        return ReconciliationReport(to_eth(self.origin_amount_wei),to_eth(tracked),
            to_eth(gas),to_eth(unaccounted),unaccounted == 0,len(endpoints),len(graph.all_nodes))
