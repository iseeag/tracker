import ccxt
import asyncio
import pandas as pd
from typing import Dict, List
import aiohttp

class AssetTracker:
    def __init__(self, api_key: str, api_secret: str):
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
    
    async def get_spot_balance(self) -> Dict:
        balance = self.exchange.fetch_balance()
        total = balance['total']
        return {k: v for k, v in total.items() if v > 0}
    
    async def get_funding_balance(self) -> Dict:
        try:
            funding = self.exchange.fetch_funding_balance()
            return {k: v['free'] for k, v in funding.items() if v['free'] > 0}
        except:

            return {}
    
    async def get_futures_balance(self) -> Dict:
        try:
            futures = self.exchange.fetch_balance({'type': 'future'})
            return {k: v['total'] for k, v in futures.items() if v['total'] > 0}
        except:
            return {}
    
    async def get_earning_balance(self) -> Dict:
        try:
            earnings = self.exchange.fetch_lending_positions()
            return {pos['currency']: pos['total'] for pos in earnings}
        except:
            return {}
    
    async def get_spot_positions(self) -> List[Dict]:
        try:
            positions = []
            markets = self.exchange.load_markets()
            for symbol in markets:
                if symbol.endswith('/USDT'):
                    try:
                        ticker = self.exchange.fetch_ticker(symbol)
                        positions.append({
                            'symbol': symbol,
                            'price': ticker['last'],
                            'change': ticker['percentage']
                        })
                    except:
                        continue
            return positions
        except:
            return []
    
    async def get_futures_positions(self) -> List[Dict]:
        try:
            positions = self.exchange.fetch_positions()
            return [pos for pos in positions if float(pos['contracts']) > 0]
        except:
            return []
    
    async def get_all_data(self) -> Dict:
        tasks = [
            self.get_spot_balance(),
            self.get_funding_balance(),
            self.get_futures_balance(),
            self.get_earning_balance(),
            self.get_spot_positions(),
            self.get_futures_positions()
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            'spot_balance': results[0],
            'funding_balance': results[1],
            'futures_balance': results[2],
            'earning_balance': results[3],
            'spot_positions': results[4],
            'futures_positions': results[5]
        }
    
    def calculate_total_value(self, data: Dict) -> Dict:
        total_spot = sum(
            amount * self.exchange.fetch_ticker(f"{currency}/USDT")['last']
            for currency, amount in data['spot_balance'].items()
        )
        
        total_funding = sum(
            amount * self.exchange.fetch_ticker(f"{currency}/USDT")['last']
            for currency, amount in data['funding_balance'].items()
        )
        
        total_futures = sum(
            float(pos['notional'])
            for pos in data['futures_positions']
        )
        
        total_earning = sum(
            amount * self.exchange.fetch_ticker(f"{currency}/USDT")['last']
            for currency, amount in data['earning_balance'].items()
        )
        
        total_value = total_spot + total_funding + total_futures + total_earning
        
        return {
            'total_value': total_value,
            'total_spot': total_spot,
            'total_funding': total_funding,
            'total_futures': total_futures,
            'total_earning': total_earning
        }
