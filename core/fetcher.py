import hashlib
import logging
import time
from typing import Any, Dict, List, Optional
import requests
import config

logger = logging.getLogger(__name__)

MOCK_EXCHANGE_ENDPOINTS = {
    "0x28c6c06298d514db089934071355e5743bf21d60",
    "0x70e24f392c54e428e6170ba9c4320ed643a6d909",
}


class BlockchainFetcher:
    """Etherscan API V2 fetcher with retry handling and deterministic demo data."""
    def __init__(self, api_key: Optional[str] = None, use_mock: bool = False) -> None:
        self.api_key = (api_key or config.ETHERSCAN_API_KEY).strip()
        self.api_url = config.ETHERSCAN_API_URL
        self.headers = config.REQUEST_HEADERS
        self.session = requests.Session()
        self.use_mock = use_mock

    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("No Etherscan API key configured. Add it in the sidebar or use Demo mode.")
        params["apikey"] = self.api_key
        params["chainid"] = config.DEFAULT_CHAIN_ID
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                response = self.session.get(self.api_url, params=params,
                    headers=self.headers, timeout=config.DEFAULT_TIMEOUT_SECONDS)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "0" and data.get("message") == "NOTOK":
                    raise ValueError(f"Etherscan API error: {data.get('result', 'Unknown error')}")
                return data
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                if attempt == config.MAX_RETRIES:
                    raise RuntimeError(f"API request failed after {config.MAX_RETRIES} attempts: {exc}") from exc
                logger.warning("Request attempt %s failed: %s", attempt, exc)
                time.sleep(1)
        return {}

    @staticmethod
    def wei_to_eth(value: int) -> float:
        return int(value) / 10**18

    def _get_mock_data(self, tx_hash: str) -> Dict[str, Any]:
        return {"tx_hash": tx_hash,
            "from_address": "0x1111111111111111111111111111111111111111",
            "to_address": "0x0941dfaa0db804f37df1273e04cf10d55e6ffebffb80",
            "value_wei": 10 * 10**18, "value_eth": 10.0,
            "gas_price_wei": 20_000_000_000, "gas_used": 21000,
            "gas_fee_eth": 0.00042, "block_number": 18000000}

    def get_transaction_details(self, tx_hash: str) -> Dict[str, Any]:
        clean = tx_hash.strip().lower()
        if self.use_mock:
            return self._get_mock_data(clean)
        try:
            tx = self._make_request({"module":"proxy","action":"eth_getTransactionByHash","txhash":clean}).get("result")
            if not tx or not isinstance(tx, dict) or "from" not in tx:
                raise RuntimeError("Transaction was not found or has no sender.")
            receipt = self._make_request({"module":"proxy","action":"eth_getTransactionReceipt","txhash":clean}).get("result") or {}
            value = int(tx.get("value", "0x0"), 16)
            gas_price = int(tx.get("gasPrice", "0x0"), 16)
            gas_used = int(receipt.get("gasUsed", "0x0"), 16)
            return {"tx_hash":clean, "from_address":tx.get("from","").lower(),
                "to_address":(tx.get("to") or "").lower(), "value_wei":value,
                "value_eth":self.wei_to_eth(value), "gas_price_wei":gas_price,
                "gas_used":gas_used, "gas_fee_eth":self.wei_to_eth(gas_price*gas_used),
                "block_number":int(tx.get("blockNumber","0x0"),16)}
        except Exception as exc:
            raise RuntimeError(f"Unable to fetch transaction {clean}: {exc}") from exc

    def get_wallet_start_details(self, address: str) -> Dict[str, Any]:
        clean = address.strip().lower()
        if self.use_mock:
            balance = 10 * 10**18
        else:
            raw = self._make_request({"module":"account","action":"balance",
                "address":clean,"tag":"latest"})
            try:
                balance = int(raw.get("result","0"))
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"Invalid balance response for {clean}") from exc
        return {"tx_hash":f"wallet:{clean}", "from_address":clean, "to_address":clean,
            "value_wei":balance, "value_eth":self.wei_to_eth(balance),
            "gas_price_wei":0,"gas_used":0,"gas_fee_eth":0.0,"block_number":0}

    def get_outgoing_transactions(self, address: str,
            max_transactions: int = config.DEFAULT_MAX_TRANSACTIONS) -> List[Dict[str, Any]]:
        target = address.strip().lower()
        if self.use_mock:
            if target in MOCK_EXCHANGE_ENDPOINTS:
                return []
            if target == "0x0941dfaa0db804f37df1273e04cf10d55e6ffebffb80":
                children = ["0x28c6c06298d514db089934071355e5743bf21d60",
                            "0x70e24f392c54e428e6170ba9c4320ed643a6d909"]
            else:
                children = ["0x"+hashlib.sha256(f"{target}:child:{i}".encode()).hexdigest()[-40:] for i in (1,2)]
            return [
                {"tx_hash":"0x"+hashlib.sha256(f"{target}:tx:1".encode()).hexdigest(),
                 "from_address":target,"to_address":children[0],"value_wei":6*10**18,
                 "value_eth":6.0,"gas_price_wei":20_000_000_000,"gas_used":21000,
                 "gas_fee_eth":0.00042,"block_number":18000001,"timestamp":1690000000},
                {"tx_hash":"0x"+hashlib.sha256(f"{target}:tx:2".encode()).hexdigest(),
                 "from_address":target,"to_address":children[1],"value_wei":3_990_000_000_000_000_000,
                 "value_eth":3.99,"gas_price_wei":20_000_000_000,"gas_used":21000,
                 "gas_fee_eth":0.00042,"block_number":18000002,"timestamp":1690000100}
            ][:max_transactions]
        params = {"module":"account","action":"txlist","address":target,
            "startblock":0,"endblock":99999999,"page":1,"offset":max_transactions,"sort":"asc"}
        tx_list = self._make_request(params).get("result", [])
        if not isinstance(tx_list, list):
            return []
        outgoing = []
        for tx in tx_list:
            if tx.get("from","").lower() == target and tx.get("isError") == "0" and tx.get("to"):
                value = int(tx.get("value","0"))
                gas_price = int(tx.get("gasPrice","0"))
                gas_used = int(tx.get("gasUsed","0"))
                outgoing.append({"tx_hash":tx.get("hash"),"from_address":target,
                    "to_address":tx["to"].lower(),"value_wei":value,"value_eth":self.wei_to_eth(value),
                    "gas_price_wei":gas_price,"gas_used":gas_used,
                    "gas_fee_eth":self.wei_to_eth(gas_price*gas_used),
                    "block_number":int(tx.get("blockNumber","0")),
                    "timestamp":int(tx.get("timeStamp","0"))})
        return outgoing[:max_transactions]
