import asyncio
from traceback import format_exc
from typing import Dict, List

from binance import AsyncClient, Client
from loguru import logger


class SimpleAssetTracker:
    def __init__(self, api_key: str, api_secret: str):
        logger.debug("Initializing SimpleAssetTracker")
        self.client = Client(api_key, api_secret)
        self.async_client: AsyncClient = None

    async def _ensure_async_client(self):
        if self.async_client is None:
            self.async_client = await AsyncClient.create(
                api_key=self.client.API_KEY,
                api_secret=self.client.API_SECRET
            )

    async def _get_all_usdt_prices(self) -> Dict[str, float]:
        """Get all USDT prices in one API call."""
        try:
            tickers = await self.async_client.get_symbol_ticker()
            # Create price lookup dictionary for both USDT and BTC pairs
            prices = {}
            btc_prices = {}
            btc_usdt_price = None

            for ticker in tickers:
                symbol = ticker['symbol']
                price = float(ticker['price'])

                if symbol.endswith('USDT'):
                    base = symbol[:-4]  # Remove 'USDT'
                    prices[base] = price
                elif symbol.endswith('BTC'):
                    base = symbol[:-3]  # Remove 'BTC'
                    btc_prices[base] = price
                if symbol == 'BTCUSDT':
                    btc_usdt_price = price

            # For tokens without USDT pairs, try to calculate via BTC
            if btc_usdt_price:
                for base, btc_price in btc_prices.items():
                    if base not in prices:
                        prices[base] = btc_price * btc_usdt_price

            # Add USDT price
            prices['USDT'] = 1.0

            return prices
        except Exception as e:
            logger.error(f"Error fetching prices: {str(e)}\n{format_exc()}")
            return {'USDT': 1.0}

    async def get_spot_breakdown(self) -> Dict:
        """Get spot account breakdown."""
        try:
            await self._ensure_async_client()
            account = await self.async_client.get_account()
            prices = await self._get_all_usdt_prices()

            total_value = sum(
                float(asset['free']) * prices.get(asset['asset'], 0) +
                float(asset['locked']) * prices.get(asset['asset'], 0)
                for asset in account['balances']
                if float(asset['free']) + float(asset['locked']) > 0
            )

            return {
                'total_value': total_value,
                'raw_data': account
            }
        except Exception as e:
            logger.error(f"Error fetching spot breakdown: {str(e)}\n{format_exc()}")
            return {'total_value': 0, 'raw_data': {}}

    async def get_futures_breakdown(self) -> Dict:
        """Get futures account breakdown."""
        try:
            await self._ensure_async_client()
            account = await self.async_client.futures_account()
            prices = await self._get_all_usdt_prices()

            # Get USDT-M futures balances
            futures_balances = await self.async_client.futures_account_balance()
            futures_total = sum(float(asset['balance']) for asset in futures_balances)
            futures_upnl = sum(float(asset['crossUnPnl']) for asset in futures_balances)

            # Get Coin-M futures balances and convert to USDT
            coin_futures_balances = await self.async_client.futures_coin_account_balance()
            coin_futures_total = sum(
                float(asset['balance']) * prices.get(asset['asset'], 0)
                for asset in coin_futures_balances
            )
            coin_futures_upnl = sum(
                float(asset['crossUnPnl']) * prices.get(asset['asset'], 0)
                for asset in coin_futures_balances
            )

            # Log warnings for missing prices
            for asset in coin_futures_balances:
                if asset['asset'] not in prices and (
                        float(asset['balance']) != 0 or float(asset['crossUnPnl']) != 0
                ):
                    logger.warning(f"No price found for coin-margined futures asset: {asset['asset']}")

            return {
                'wallet_balance': float(account['totalWalletBalance']) + coin_futures_total,  # add coin futures balance
                'unrealized_pnl': float(account['totalUnrealizedProfit']) + coin_futures_upnl,  # add coin futures upnl
                'margin_balance': float(account['totalMarginBalance']),
                'cross_wallet_balance': float(account['totalCrossWalletBalance']),
                'cross_upnl': float(account['totalCrossUnPnl']),
                'available_balance': float(account['availableBalance']),
                'futures_breakdown': {
                    'total_balance': futures_total,
                    'total_upnl': futures_upnl
                },
                'coin_futures_breakdown': {
                    'total_balance': coin_futures_total,
                    'total_upnl': coin_futures_upnl
                },
                'raw_data': account
            }
        except Exception as e:
            logger.error(f"Error fetching futures breakdown: {str(e)}\n{format_exc()}")
            return {
                'wallet_balance': 0,
                'unrealized_pnl': 0,
                'margin_balance': 0,
                'cross_wallet_balance': 0,
                'cross_upnl': 0,
                'available_balance': 0,
                'futures_breakdown': {'total_balance': 0, 'total_upnl': 0},
                'coin_futures_breakdown': {'total_balance': 0, 'total_upnl': 0},
                'raw_data': {}
            }

    async def get_margin_breakdown(self) -> Dict:
        """Get margin account breakdown."""
        try:
            await self._ensure_async_client()
            account = await self.async_client.get_margin_account()

            # Get BTC price for conversion
            prices = await self._get_all_usdt_prices()
            btc_price = prices.get('BTC', 0)

            return {
                'total_asset_btc': float(account['totalAssetOfBtc']),
                'total_liability_btc': float(account['totalLiabilityOfBtc']),
                'total_net_asset_btc': float(account['totalNetAssetOfBtc']),
                'total_asset_usd': float(account['totalAssetOfBtc']) * btc_price,
                'total_liability_usd': float(account['totalLiabilityOfBtc']) * btc_price,
                'total_net_asset_usd': float(account['totalNetAssetOfBtc']) * btc_price,
                'raw_data': account
            }
        except Exception as e:
            logger.error(f"Error fetching margin breakdown: {str(e)}\n{format_exc()}")
            return {
                'total_asset_btc': 0,
                'total_liability_btc': 0,
                'total_net_asset_btc': 0,
                'total_asset_usd': 0,
                'total_liability_usd': 0,
                'total_net_asset_usd': 0,
                'raw_data': {}
            }

    async def get_all_breakdowns(self) -> Dict:
        """Get all account breakdowns."""
        try:
            await self._ensure_async_client()

            spot = await self.get_spot_breakdown()
            futures = await self.get_futures_breakdown()
            margin = await self.get_margin_breakdown()

            total_value = (
                    spot['total_value'] +  # Spot value
                    futures['wallet_balance'] + futures['unrealized_pnl'] +  # Futures value including unrealized PnL
                    margin['total_net_asset_usd']  # Margin net value in USD
            )

            return {
                'total_value': total_value,
                'spot_breakdown': spot,
                'futures_breakdown': futures,
                'margin_breakdown': margin
            }
        except Exception as e:
            logger.error(f"Error fetching all breakdowns: {str(e)}\n{format_exc()}")
            return {
                'total_value': 0,
                'spot_breakdown': {'total_value': 0, 'raw_data': {}},
                'futures_breakdown': {
                    'wallet_balance': 0,
                    'unrealized_pnl': 0,
                    'margin_balance': 0,
                    'cross_wallet_balance': 0,
                    'cross_upnl': 0,
                    'available_balance': 0,
                    'futures_breakdown': {'total_balance': 0, 'total_upnl': 0},
                    'coin_futures_breakdown': {'total_balance': 0, 'total_upnl': 0},
                    'raw_data': {}
                },
                'margin_breakdown': {
                    'total_asset_btc': 0,
                    'total_liability_btc': 0,
                    'total_net_asset_btc': 0,
                    'total_asset_usd': 0,
                    'total_liability_usd': 0,
                    'total_net_asset_usd': 0,
                    'raw_data': {}
                }
            }
