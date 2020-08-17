from PySide2.QtGui import QColor

class Setup:
    DB_PATH = "ledger.sqlite"
    INIT_SCRIPT_PATH = 'ledger.sql'
    TARGET_SCHEMA = 4
    CALC_TOLERANCE = 1e-10
    DISP_TOLERANCE = 1e-4


class BookAccount:  # PREDEFINED BOOK ACCOUNTSК
    Costs = 1
    Incomes = 2
    Money = 3
    Assets = 4
    Liabilities = 5
    Transfers = 6

class TransactionType:   # PREDEFINED TRANSACTION TYPES
    Action = 1
    Dividend = 2
    Trade = 3
    Transfer = 4

# TRANSFER SUB-TYPES
TRANSFER_FEE = 0
TRANSFER_OUT = -1
TRANSFER_IN = 1

# CORPORATE ACTIONS FOR ASSETS
CORP_ACTION_CONVERSION = 1
CORP_ACTION_SPINOFF = 2

# PREDEFINED CATEGORIES
CATEGORY_FEES = 5
CATEGORY_TAXES = 6
CATEGORY_DIVIDEND = 7
CATEGORY_INTEREST = 8
CATEGORY_PROFIT = 9

# PREDEFINED ASSET TYPES
ASSET_TYPE_MONEY = 1
ASSET_TYPE_STOCK = 2
ASSET_TYPE_BOND = 3
ASSET_TYPE_ETF = 4

# PREDEFINED PEERS
PEER_FINANCIAL = 1

# PREDEFINED DATA FEEDS
FEED_NONE = -1
FEED_CBR = 0
FEED_RU = 1
FEED_US = 2
FEED_EU = 3

DARK_GREEN_COLOR = QColor(0, 100, 0)
DARK_RED_COLOR = QColor(139, 0, 0)
DARK_BLUE_COLOR = QColor(0, 0, 139)
BLUE_COLOR = QColor(0, 0, 255)
LIGHT_BLUE_COLOR = QColor(150, 200, 255)
LIGHT_PURPLE_COLOR = QColor(200, 150, 255)
LIGHT_GREEN_COLOR = QColor(127, 255, 127)
LIGHT_RED_COLOR = QColor(255, 127, 127)
LIGHT_YELLOW_COLOR = QColor(255, 255, 200)

TAB_ACTION = 0
TAB_DIVIDEND = 2
TAB_TRADE = 1
TAB_TRANSFER = 3
