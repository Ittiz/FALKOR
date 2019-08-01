from tradeexecution.MoneyTrader import MoneyTrader
from exchangeoperators.BinanceOperator import BinanceOperator


class BinanceMoneyTrader(MoneyTrader):
    """TradeExecutor for the Binance cryptocurrency exchange"""

    def __init__(self, client_id, client_secret):
        self.op = BinanceOperator(client_id, client_secret)

    def buy_limit_order(self, symbol, quantity, price):
        pass

    def sell_limit_order(self, symbol, quantity, price):
        raise NotImplementedError

    def buy_market_order(self, symbol, quantity, price):
        raise NotImplementedError

    def sell_market_order(self, symbol, quantity, price):
        raise NotImplementedError

    def order_status(self, symbol, order_id):
        raise NotImplementedError

    def cancel_order(self, symbol, order_id):
        raise NotImplementedError

    def get_open_orders(self):
        raise NotImplementedError

    def get_all_orders(self):
        raise NotImplementedError
