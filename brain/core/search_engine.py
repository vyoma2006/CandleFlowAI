import pandas as pd
import requests
from typing import List, Dict, Any

class TrieNode:
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_end_of_word: bool = False
        self.associated_data: List[Dict[str, str]] = []

class StockTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str, data: Dict[str, str]):
        """Inserts a normalized string token character-by-character into the prefix tree."""
        node = self.root
        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            # Optimization: Cache records along the traversal path for O(L) instant lookups
            if data not in node.associated_data:
                node.associated_data.append(data)
        node.is_end_of_word = True

    def search_prefix(self, prefix: str) -> List[Dict[str, str]]:
        """Traverses down the tree keys to retrieve all matches starting with the prefix."""
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]
        return node.associated_data


class OptimizedSearchEngine:
    def __init__(self):
        self.symbol_trie = StockTrie()
        self.stock_list: List[Dict[str, str]] = []
        self._load_and_index_dataset()

    def _load_and_index_dataset(self):
        """🚀 DYNAMIC SEEDER: Pulls thousands of rows from the master NSE directory

        directly into memory cache on application boot.
        """
        print("📡 Initializing Master Search Core Engine Network Buffers...")
        try:
            # High-speed verified master JSON file mirror containing all listed NSE companies
            url = "https://raw.githubusercontent.com/themetavoice/nse-ticker-symbols/main/nse_tickers.json"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                raw_data = response.json() # Returns a dictionary format: {"SYMBOL": "Company Name"}
                
                # Transform thousands of dictionary rows into clean query records dynamically
                self.stock_list = [
                    {"symbol": f"{symbol}.NS", "name": name.strip()}
                    for symbol, name in raw_data.items()
                ]
                
                # Feed the complete stock universe into our Trie and list systems from A to Z
                for item in self.stock_list:
                    clean_symbol = item['symbol'].replace('.NS', '').lower()
                    self.symbol_trie.insert(clean_symbol, item)
                    
                print(f"✅ Search Engine Online: Loaded {len(self.stock_list)} dynamic NSE assets in RAM cache!")
                return
                
        except Exception as e:
            print(f"🚨 Remote master channel timeout ({e}). Deploying emergency backup grid layout.")
            
        # Emergency hard-coded baseline fallback matrix if laptop loses internet connectivity
        fallback_data = {
            "ADANIENT": "Adani Enterprises Ltd", "AXISBANK": "Axis Bank Ltd",
            "BAJFINANCE": "Bajaj Finance Ltd", "BHARTIARTL": "Bharti Airtel Ltd",
            "COALINDIA": "Coal India Ltd", "FEDERALBNK": "The Federal Bank Ltd",
            "HDFCBANK": "HDFC Bank Ltd", "HINDUNILVR": "Hindustan Unilever Ltd",
            "INFY": "Infosys Ltd", "ITC": "ITC Ltd", "ICICIBANK": "ICICI Bank Ltd",
            "JSWSTEEL": "JSW Steel Ltd", "MARUTI": "Maruti Suzuki India Ltd",
            "NESTLEIND": "Nestle India Ltd", "RELIANCE": "Reliance Industries Ltd",
            "SBIN": "State Bank of India", "SUNPHARMA": "Sun Pharmaceutical Industries Ltd",
            "TCS": "Tata Consultancy Services Ltd", "TATASTEEL": "Tata Steel Ltd",
            "TITAN": "Titan Company Ltd", "WIPRO": "Wipro Ltd"
        }
        self.stock_list = [
            {"symbol": f"{s}.NS", "name": n}
            for s, n in fallback_data.items()
        ]
        for item in self.stock_list:
            clean_symbol = item['symbol'].replace('.NS', '').lower()
            self.symbol_trie.insert(clean_symbol, item)

    def query(self, text_token: str, max_limit: int = 8) -> List[Dict[str, Any]]:
        """Executes high-speed hybrid search: returns alphabetical prefix matches

        first, then fills slots using partial substring checks.
        """
        query_clean = text_token.lower().strip()
        if not query_clean:
            return []

        prefix_matches = []
        substring_matches = []
        seen_symbols = set()

        # PATH 1: Instant Prefix tree extraction (e.g., Typing "b" -> Bajaj, Bharti)
        trie_matches = self.symbol_trie.search_prefix(query_clean)
        for match in trie_matches:
            # Extra safety block checks if ticker code OR name explicitly starts with your character query
            stock_code = match["symbol"].split('.')[0].lower()
            stock_name = match["name"].lower().strip()
            
            if stock_code.startswith(query_clean) or stock_name.startswith(query_clean):
                prefix_matches.append(match)
                seen_symbols.add(match['symbol'])

        # PATH 2: Multi-character internal phrase lookups (e.g., Typing "bank" -> HDFC Bank, ICICI Bank)
        for item in self.stock_list:
            symbol_tag = item['symbol']
            if symbol_tag not in seen_symbols:
                stock_code = item["symbol"].split('.')[0].lower()
                stock_name = item["name"].lower()
                
                if query_clean in stock_code or query_clean in stock_name:
                    substring_matches.append(item)
                    seen_symbols.add(symbol_tag)

        # Alphabetize each category separately to keep the interface looking clean and organized
        prefix_matches = sorted(prefix_matches, key=lambda x: x['name'])
        substring_matches = sorted(substring_matches, key=lambda x: x['name'])

        # Append them together—Starters claim top priority, partials handle fallback gaps
        final_results = prefix_matches + substring_matches
        return final_results[:max_limit]