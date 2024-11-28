import asyncio
from traceback import format_exc
from typing import Dict, List

import ccxt
from loguru import logger


class AssetTracker:
    def __init__(self, api_key: str, api_secret: str):
        logger.debug("Initializing AssetTracker")
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
    
    async def get_spot_balance(self) -> Dict:
        try:
            balance = self.exchange.fetch_balance()
            total = balance['total']
            result = {k: v for k, v in total.items() if v > 0}
            logger.debug(f"Spot balance fetched: {len(result)} assets")
            return result
        except Exception as e:
            logger.error(f"Error fetching spot balance: {str(e)}\n{format_exc()}")
            return {}
    
    async def get_funding_balance(self) -> Dict:
        try:
            funding = self.exchange.fetch_funding_balance()
            result = {k: v['free'] for k, v in funding.items() if v['free'] > 0}
            logger.debug(f"Funding balance fetched: {len(result)} assets")
            return result
        except Exception as e:
            logger.error(f"Error fetching funding balance: {str(e)}\n{format_exc()}")
            return {}
    
    async def get_futures_balance(self) -> Dict:
        try:
            futures = self.exchange.fetch_balance({'type': 'future'})
            result = {k: v['total'] for k, v in futures.items() if v['total'] > 0}
            logger.debug(f"Futures balance fetched: {len(result)} assets")
            return result
        except Exception as e:
            logger.error(f"Error fetching futures balance: {str(e)}\n{format_exc()}")
            return {}
    
    async def get_earning_balance(self) -> Dict:
        try:
            earnings = self.exchange.fetch_lending_positions()
            result = {pos['currency']: pos['total'] for pos in earnings}
            logger.debug(f"Earning balance fetched: {len(result)} assets")
            return result
        except Exception as e:
            logger.error(f"Error fetching earning balance: {str(e)}\n{format_exc()}")
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
                    except Exception as e:
                        logger.error(f"Error fetching spot position for {symbol}: {str(e)}\n{format_exc()}")
                        continue
            logger.debug(f"Spot positions fetched: {len(positions)} assets")
            return positions
        except Exception as e:
            logger.error(f"Error fetching spot positions: {str(e)}\n{format_exc()}")
            return []
    
    async def get_futures_positions(self) -> List[Dict]:
        try:
            positions = self.exchange.fetch_positions()
            result = [pos for pos in positions if float(pos['contracts']) > 0]
            logger.debug(f"Futures positions fetched: {len(result)} assets")
            return result
        except Exception as e:
            logger.error(f"Error fetching futures positions: {str(e)}\n{format_exc()}")
            return []
    
    async def get_all_data(self) -> Dict:
        try:
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
        except Exception as e:
            logger.error(f"Error fetching all data: {str(e)}\n{format_exc()}")
            return {}
    
    def calculate_total_value(self, data: Dict) -> Dict:
        try:
            total_spot = sum(
                amount if currency == 'USDT' else
                amount * self.exchange.fetch_ticker(f"{currency}/USDT")['last']
                for currency, amount in data['spot_balance'].items()
            )
            
            total_funding = sum(
                amount if currency == 'USDT' else
                amount * self.exchange.fetch_ticker(f"{currency}/USDT")['last']
                for currency, amount in data['funding_balance'].items()
            )
            
            total_futures = sum(
                float(pos['notional'])
                for pos in data['futures_positions']
            )
            
            total_earning = sum(
                amount if currency == 'USDT' else
                amount * self.exchange.fetch_ticker(f"{currency}/USDT")['last']
                for currency, amount in data['earning_balance'].items()
            )
            
            total_value = total_spot + total_funding + total_futures + total_earning
            
            logger.debug(f"Total value calculated: {total_value}")
            return {
                'total_value': total_value,
                'total_spot': total_spot,
                'total_funding': total_funding,
                'total_futures': total_futures,
                'total_earning': total_earning
            }
        except Exception as e:
            logger.error(f"Error calculating total value: {str(e)}\n{format_exc()}")
            return {}
