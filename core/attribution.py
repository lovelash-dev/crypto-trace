import json
from pathlib import Path
from typing import Dict, List, Optional
import config

class EntityAttributor:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.ATTRIBUTION_DB_PATH
        self.known_entities = self._load_database()
    def _load_database(self):
        if not self.db_path.exists(): return {}
        try:
            with open(self.db_path,encoding="utf-8") as handle:
                return {key.lower(): value for key,value in json.load(handle).items()}
        except (json.JSONDecodeError,OSError):
            return {}
    def get_attribution(self,address):
        return self.known_entities.get(address.lower(),{
            "entity":"Unknown Wallet","category":"Unclassified","confidence":"Low"})
    def label_graph_endpoints(self,endpoints):
        result=[]
        for node in endpoints:
            item=self.get_attribution(node.address)
            result.append({"address":node.address,"stolen_flow":node.stolen_flow,
                "entity":item["entity"],"category":item["category"],
                "confidence":item["confidence"],"source":item.get("source","Unspecified"),
                "last_verified":item.get("last_verified","Unknown")})
        return result
