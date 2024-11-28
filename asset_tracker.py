import asyncio
from traceback import format_exc
from typing import Dict, List

from binance import AsyncClient, Client
from loguru import logger


class AssetTracker:
    def __init__(self, api_key: str, api_secret: str):
        logger.debug("Initializing AssetTracker")
        self.client = Client(api_key, api_secret)
        self.async_client = None

    async def _ensure_async_client(self):
        if self.async_client is None:
            self.async_client = await AsyncClient.create(
                api_key=self.client.API_KEY,
                api_secret=self.client.API_SECRET
            )

    async def _get_usdt_price(self, symbol: str) -> float:
        """Get USDT price for a symbol."""
        if symbol == 'USDT':
            return 1.0

        try:
            ticker = await self.async_client.get_symbol_ticker(symbol=f"{symbol}USDT")
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}USDT: {str(e)}")
            return 0.0

    async def get_spot_balance(self) -> Dict:
        """Get spot wallet balances."""
        try:
            await self._ensure_async_client()
            account = await self.async_client.get_account()
            result = {
                asset['asset']: float(asset['free']) + float(asset['locked'])
                for asset in account['balances']
                if float(asset['free']) + float(asset['locked']) > 0
            }
            logger.debug(f"Spot balance fetched: {len(result)} assets")
            return result
        except Exception as e:
            logger.error(f"Error fetching spot balance: {str(e)}\n{format_exc()}")
            return {}

    async def get_margin_balance(self) -> Dict:
        """Get cross margin account balances."""
        try:
            await self._ensure_async_client()
            account = await self.async_client.get_margin_account()
            result = {
                asset['asset']: float(asset['netAsset'])
                for asset in account['userAssets']
                if float(asset['netAsset']) != 0
            }
            logger.debug(f"Margin balance fetched: {len(result)} assets")
            return result
        except Exception as e:
            logger.error(f"Error fetching margin balance: {str(e)}\n{format_exc()}")
            return {}

    async def get_futures_balance(self) -> Dict:
        """Get USDT-M futures account balances."""
        try:
            await self._ensure_async_client()
            account = await self.async_client.futures_account()
            result = {
                asset['asset']: float(asset['balance'])
                for asset in account['assets']
                if float(asset['balance']) != 0
            }
            logger.debug(f"Futures balance fetched: {len(result)} assets")
            return result
        except Exception as e:
            logger.error(f"Error fetching futures balance: {str(e)}\n{format_exc()}")
            return {}

    async def get_futures_positions(self) -> List[Dict]:
        """Get USDT-M futures positions."""
        try:
            await self._ensure_async_client()
            positions = await self.async_client.futures_position_information()
            result = [
                {
                    'symbol': pos['symbol'],
                    'amount': float(pos['positionAmt']),
                    'entryPrice': float(pos['entryPrice']),
                    'markPrice': float(pos['markPrice']),
                    'unPnl': float(pos['unRealizedProfit']),
                    'leverage': int(pos['leverage']),
                    'notional': abs(float(pos['positionAmt']) * float(pos['markPrice']))
                }
                for pos in positions
                if float(pos['positionAmt']) != 0
            ]
            logger.debug(f"Futures positions fetched: {len(result)} positions")
            return result
        except Exception as e:
            logger.error(f"Error fetching futures positions: {str(e)}\n{format_exc()}")
            return []

    async def get_all_data(self) -> Dict:
        """Fetch all balances and positions."""
        try:
            await self._ensure_async_client()
            
            tasks = [
                self.get_spot_balance(),
                self.get_margin_balance(),
                self.get_futures_balance(),
                self.get_futures_positions(),
            ]

            spot, margin, futures_balance, futures_positions = await asyncio.gather(*tasks)

            return {
                'spot_balance': spot,
                'margin_balance': margin,
                'futures_balance': futures_balance,
                'futures_positions': futures_positions,
            }
        except Exception as e:
            logger.error(f"Error fetching all data: {str(e)}\n{format_exc()}")
            return {
                'spot_balance': {},
                'margin_balance': {},
                'futures_balance': {},
                'futures_positions': [],
            }

    async def calculate_total_value(self, data: Dict) -> Dict:
        """Calculate total portfolio value in USDT."""
        try:
            await self._ensure_async_client()

            # Calculate spot value
            spot_tasks = [
                self._get_usdt_price(currency) for currency in data['spot_balance'].keys()
            ]
            spot_prices = await asyncio.gather(*spot_tasks)
            total_spot = sum(
                amount * price
                for (currency, amount), price in zip(data['spot_balance'].items(), spot_prices)
            )

            # Calculate margin value
            margin_tasks = [
                self._get_usdt_price(currency) for currency in data['margin_balance'].keys()
            ]
            margin_prices = await asyncio.gather(*margin_tasks)
            total_margin = sum(
                amount * price
                for (currency, amount), price in zip(data['margin_balance'].items(), margin_prices)
            )

            # Calculate futures value (includes unrealized PnL)
            total_futures = sum(
                float(pos['notional']) for pos in data['futures_positions']
            )
            futures_pnl = sum(
                float(pos['unPnl']) for pos in data['futures_positions']
            )

            total_value = total_spot + total_margin + total_futures + futures_pnl

            logger.debug(f"Total value calculated: {total_value:.2f} USDT")
            logger.debug(
                f"Breakdown - Spot: {total_spot:.2f}, Margin: {total_margin:.2f}, "
                f"Futures: {total_futures:.2f} (PnL: {futures_pnl:.2f})"
            )

            return {
                'total_value': total_value,
                'total_spot': total_spot,
                'total_margin': total_margin,
                'total_futures': total_futures + futures_pnl,
                'futures_pnl': futures_pnl
            }
        except Exception as e:
            logger.error(f"Error calculating total value: {str(e)}\n{format_exc()}")
            return {
                'total_value': 0,
                'total_spot': 0,
                'total_margin': 0,
                'total_futures': 0,
                'futures_pnl': 0
            }
