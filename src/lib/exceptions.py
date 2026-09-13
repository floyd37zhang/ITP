class MySQLClientError(Exception):
    pass


class ConnectionError(MySQLClientError):
    pass


class QueryError(MySQLClientError):
    pass


class TransactionError(MySQLClientError):
    pass


class PoolExhaustedError(MySQLClientError):
    pass