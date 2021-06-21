import logging
import re
from datetime import datetime, timezone

from jal.widgets.helpers import g_tr
from jal.db.update import JalDB
from jal.constants import Setup, PredefinedCategory, PredefinedAsset
from jal.data_import.statement import FOF
from jal.data_import.statement_xls import StatementXLS, XLS_ParseError


class StatementUKFU(StatementXLS):
    Header = (2, 0, '  Брокер: ООО "УРАЛСИБ Брокер"')
    PeriodPattern = (2, 2, r"  за период с (?P<S>\d\d\.\d\d\.\d\d\d\d) по (?P<E>\d\d\.\d\d\.\d\d\d\d)")
    AccountPattern = (2, 7, None)
    SummaryHeader = "СОСТОЯНИЕ ДЕНЕЖНЫХ СРЕДСТВ НА СЧЕТЕ"
    trade_columns = {
        "number": "Номер сделки",
        "date": "Дата сделки",
        "time": "Время сделки",
        "settlement": "Дата поставки, плановая",
        "isin": "ISIN",
        "B/S": "Вид сделки",
        "price": "Цена одной ЦБ",
        "qty": "Количество ЦБ, шт.",
        "amount": "Сумма сделки",
        "accrued_int": "НКД",
        "fee_ex": "Комиссия ТС",
        "currency": "Валюта цены"
    }

    asset_section = "СОСТОЯНИЕ ПОРТФЕЛЯ ЦЕННЫХ БУМАГ"
    asset_columns = {
        "name": "Наименование ЦБ",
        "isin": "ISIN",
        "reg_code": "Номер гос. регистрации / CFI код"
    }

    def __init__(self):
        super().__init__()
        self.StatementName = g_tr("UKFU", "Uralsib broker")

    def _load_deals(self):
        self.load_stock_deals()
        self.load_futures_deals()

    def _load_cash_transactions(self):
        self.load_cash_transactions()
        self.load_broker_fee()

    def load_stock_deals(self):
        cnt = 0
        columns = {
            "number": "Номер сделки",
            "date": "Дата сделки",
            "time": "Время сделки",
            "isin": "ISIN",
            "B/S": "Вид сделки",
            "price": "Цена одной ЦБ",
            "currency": "Валюта цены",
            "qty": r"Количество ЦБ, шт\.",
            "amount": "Сумма сделки",
            "accrued_int": "НКД",
            "settlement": "Дата поставки, плановая",
            "fee_ex": "Комиссия ТС"
        }

        row, headers = self.find_section_start("СДЕЛКИ С ЦЕННЫМИ БУМАГАМИ", columns,
                                               subtitle="Биржевые сделки с ценными бумагами в отчетном периоде",
                                               header_height=2)
        if row < 0:
            return
        while row < self._statement.shape[0]:
            if self._statement[self.HeaderCol][row] == '' and self._statement[self.HeaderCol][row + 1] == '':
                break
            if self._statement[self.HeaderCol][row].startswith('Итого по выпуску:') or \
                    self._statement[self.HeaderCol][row] == '':
                row += 1
                continue
            try:
                deal_number = int(self._statement[self.HeaderCol][row])
            except ValueError:
                row += 1
                continue
            isin = self._statement[headers['isin']][row]
            asset_id = self._find_asset_id(isin=isin)
            if not asset_id:
                asset_id = self._add_asset(isin, '', '')
            if self._statement[headers['B/S']][row] == 'Покупка':
                qty = self._statement[headers['qty']][row]
                bond_interest = -self._statement[headers['accrued_int']][row]
            elif self._statement[headers['B/S']][row] == 'Продажа':
                qty = -self._statement[headers['qty']][row]
                bond_interest = self._statement[headers['accrued_int']][row]
            else:
                row += 1
                logging.warning(g_tr('UKFU', "Unknown trade type: ") + self._statement[headers['B/S']][row])
                continue

            price = self._statement[headers['price']][row]
            currency = self._statement[headers['currency']][row]
            fee = self._statement[headers['fee_ex']][row]
            amount = self._statement[headers['amount']][row]
            if abs(abs(price * qty) - amount) >= Setup.DISP_TOLERANCE:
                price = abs(amount / qty)
            ts_string = self._statement[headers['date']][row] + ' ' + self._statement[headers['time']][row]
            timestamp = int(datetime.strptime(ts_string, "%d.%m.%Y %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
            settlement = int(datetime.strptime(self._statement[headers['settlement']][row],
                                               "%d.%m.%Y").replace(tzinfo=timezone.utc).timestamp())
            account_id = self._find_account_id(self._account_number, currency)
            new_id = max([0] + [x['id'] for x in self._data[FOF.TRADES]]) + 1
            trade = {"id": new_id, "number": str(deal_number), "timestamp": timestamp, "settlement": settlement,
                     "account": account_id, "asset": asset_id, "quantity": qty, "price": price, "fee": fee}
            self._data[FOF.TRADES].append(trade)
            if bond_interest != 0:
                new_id = max([0] + [x['id'] for x in self._data[FOF.ASSET_PAYMENTS]]) + 1
                payment = {"id": new_id, "type": FOF.PAYMENT_INTEREST, "account": account_id, "timestamp": timestamp,
                           "number": str(deal_number), "asset": asset_id, "amount": bond_interest, "description": "НКД"}
                self._data[FOF.ASSET_PAYMENTS].append(payment)
            cnt += 1
            row += 1
        logging.info(g_tr('UKFU', "Trades loaded: ") + f"{cnt}")

    def load_futures_deals(self):
        cnt = 0
        columns = {
            "number": "Номер сделки",
            "date": "Дата сделки",
            "time": "Время сделки",
            "symbol": "Код контракта",
            "B/S": "Вид сделки",
            "price": "Цена фьючерса",
            "currency": "Валюта цены",
            "qty": r"Количество контрактов, шт\.",
            "amount": "Сумма",
            "settlement": "Дата расчетов по сделке",
            "fee_broker": r"Комиссия брокера, руб\.",
            "fee_ex": r"Комиссия ТС, руб\."
        }

        row, headers = self.find_section_start("СДЕЛКИ С ФЬЮЧЕРСАМИ И ОПЦИОНАМИ", columns,
                                               subtitle="Сделки с фьючерсами")
        if row < 0:
            return False
        while row < self._statement.shape[0]:
            if self._statement[self.HeaderCol][row] == '' and self._statement[self.HeaderCol][row + 1] == '':
                break
            if self._statement[self.HeaderCol][row].startswith("Входящая позиция по контракту") or \
                    self._statement[self.HeaderCol][row].startswith("Итого по контракту") or \
                    self._statement[self.HeaderCol][row] == '':
                row += 1
                continue
            try:
                deal_number = int(self._statement[self.HeaderCol][row])
            except ValueError:
                row += 1
                continue

            symbol = self._statement[headers['symbol']][row]
            asset_id = self._find_asset_id(symbol=symbol)
            if not asset_id:
                asset_id = self._add_asset('', '', symbol=symbol)
            if self._statement[headers['B/S']][row] == 'Покупка':
                qty = self._statement[headers['qty']][row]
            elif self._statement[headers['B/S']][row] == 'Продажа':
                qty = -self._statement[headers['qty']][row]
            else:
                row += 1
                logging.warning(g_tr('UKFU', "Unknown trade type: ") + self._statement[headers['B/S']][row])
                continue

            price = self._statement[headers['price']][row]
            currency = self._statement[headers['currency']][row]
            fee = self._statement[headers['fee_broker']][row] + self._statement[headers['fee_ex']][row]
            amount = self._statement[headers['amount']][row]
            if abs(abs(price * qty) - amount) >= Setup.DISP_TOLERANCE:
                price = abs(amount / qty)
            ts_string = self._statement[headers['date']][row] + ' ' + self._statement[headers['time']][row]
            timestamp = int(datetime.strptime(ts_string, "%d.%m.%Y %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
            settlement = int(datetime.strptime(self._statement[headers['settlement']][row],
                                               "%d.%m.%Y").replace(tzinfo=timezone.utc).timestamp())
            account_id = self._find_account_id(self._account_number, currency)
            new_id = max([0] + [x['id'] for x in self._data[FOF.TRADES]]) + 1
            trade = {"id": new_id, "number": deal_number, "timestamp": timestamp, "settlement": settlement,
                     "account": account_id, "asset": asset_id, "quantity": qty, "price": price, "fee": fee}
            self._data[FOF.TRADES].append(trade)
            cnt += 1
            row += 1
        logging.info(g_tr('UKFU', "Futures trades loaded: ") + f"{cnt}")

    def load_cash_transactions(self):
        cnt = 0
        columns = {
            "number": "№ операции",
            "date": "Дата",
            "type": "Тип операции",
            "amount": "Сумма",
            "currency": "Валюта",
            "description": "Комментарий"
        }
        operations = {
            'Ввод ДС': self.transfer_in,
            'Вывод ДС': self.transfer_out,
            'Налог': self.tax,
            'Доход по финансовым инструментам': self.dividend,
            'Погашение купона': self.interest
        }

        row, headers = self.find_section_start("ДВИЖЕНИЕ ДЕНЕЖНЫХ СРЕДСТВ ЗА ОТЧЕТНЫЙ ПЕРИОД",  columns)
        if row < 0:
            return False

        while row < self._statement.shape[0]:
            if self._statement[self.HeaderCol][row] == '' and self._statement[self.HeaderCol][row + 1] == '':
                break

            operation = self._statement[headers['type']][row]
            if operation not in operations:   # not supported type of operation
                row += 1
                continue
            number = self._statement[headers['number']][row]
            timestamp = int(datetime.strptime(self._statement[headers['date']][row],
                                              "%d.%m.%Y").replace(tzinfo=timezone.utc).timestamp())
            amount = self._statement[headers['amount']][row]
            description = self._statement[headers['description']][row]
            account_id = self._find_account_id(self._account_number, self._statement[headers['currency']][row])

            operations[operation](timestamp, number, account_id, amount, description)

            cnt += 1
            row += 1
        logging.info(g_tr('Uralsib', "Cash operations loaded: ") + f"{cnt}")

    def transfer_in(self, timestamp, number, account_id, amount, description):
        account = [x for x in self._data[FOF.ACCOUNTS] if x["id"] == account_id][0]
        new_id = max([0] + [x['id'] for x in self._data[FOF.TRANSFERS]]) + 1
        transfer = {"id": new_id, "account": [0, account_id, 0], "number": number,
                    "asset": [account['currency'], account['currency']], "timestamp": timestamp,
                    "withdrawal": amount, "deposit": amount, "fee": 0.0, "description": description}
        self._data[FOF.TRANSFERS].append(transfer)

    def transfer_out(self, timestamp, number, account_id, amount, description):
        account = [x for x in self._data[FOF.ACCOUNTS] if x["id"] == account_id][0]
        new_id = max([0] + [x['id'] for x in self._data[FOF.TRANSFERS]]) + 1
        transfer = {"id": new_id, "account": [account_id, 0, 0], "number": number,
                    "asset": [account['currency'], account['currency']], "timestamp": timestamp,
                    "withdrawal": -amount, "deposit": -amount, "fee": 0.0, "description": description}
        self._data[FOF.TRANSFERS].append(transfer)

    def dividend(self, timestamp, number, account_id, amount, description):
        DividendPattern = r"> (?P<DESCR1>.*) \((?P<REG_CODE>.*)\)((?P<DESCR2> .*)? налог в размере (?P<TAX>\d+\.\d\d) удержан)?\. НДС не облагается\."
        ISINPattern = r"[A-Z]{2}.{9}\d"

        parts = re.match(DividendPattern, description, re.IGNORECASE)
        if parts is None:
            raise XLS_ParseError(g_tr('UKFU', "Can't parse dividend description ") + f"'{description}'")
        dividend_data = parts.groupdict()
        isin_match = re.match(ISINPattern, dividend_data['REG_CODE'])
        if isin_match:
            asset_id = self._find_asset_id(isin=dividend_data['REG_CODE'])
            if not asset_id:
                asset_id = self._add_asset(isin=dividend_data['REG_CODE'], reg_code='')
        else:
            asset_id = self._find_asset_id(reg_code=dividend_data['REG_CODE'])
            if not asset_id:
                asset_id = self._add_asset(isin='', reg_code=dividend_data['REG_CODE'])

        if dividend_data['TAX']:
            try:
                tax = float(dividend_data['TAX'])
            except ValueError:
                raise XLS_ParseError(g_tr('UKFU', "Failed to convert dividend tax ") + f"'{description}'")
        else:
            tax = 0
        amount = amount + tax   # Statement contains value after taxation while JAL stores value before tax
        if dividend_data['DESCR2']:
            short_description = dividend_data['DESCR1'] + ' ' + dividend_data['DESCR2'].strip()
        else:
            short_description = dividend_data['DESCR1']
        new_id = max([0] + [x['id'] for x in self._data[FOF.ASSET_PAYMENTS]]) + 1
        payment = {"id": new_id, "type": FOF.PAYMENT_DIVIDEND, "account": account_id, "timestamp": timestamp,
                   "number": number, "asset": asset_id, "amount": amount, "tax": tax, "description": short_description}
        self._data[FOF.ASSET_PAYMENTS].append(payment)

    def interest(self, timestamp, number, account_id, amount, description):
        BondInterestPattern = r"Погашение купона №( -?\d+)? (?P<NAME>.*)"

        parts = re.match(BondInterestPattern, description, re.IGNORECASE)
        if parts is None:
            logging.error(g_tr('Uralsib', "Can't parse bond interest description ") + f"'{description}'")
            return
        interest_data = parts.groupdict()
        # FIXME make it via self._find_asset_id()
        asset_id = JalDB().find_asset_like_name(interest_data['NAME'], asset_type=PredefinedAsset.Bond)
        if asset_id is None:
            raise XLS_ParseError(g_tr('Uralsib', "Can't find asset for bond interest ") + f"'{description}'")
        new_id = max([0] + [x['id'] for x in self._data[FOF.ASSET_PAYMENTS]]) + 1
        payment = {"id": new_id, "type": FOF.PAYMENT_INTEREST, "account": account_id, "timestamp": timestamp,
                   "number": number, "asset": asset_id, "amount": amount, "description": description}
        self._data[FOF.ASSET_PAYMENTS].append(payment)

    def tax(self, timestamp, _number, account_id, amount, description):
        new_id = max([0] + [x['id'] for x in self._data[FOF.INCOME_SPENDING]]) + 1
        tax = {"id": new_id, "timestamp": timestamp, "account": account_id, "peer": 0,
               "lines": [{"amount": amount, "category": -PredefinedCategory.Taxes, "description": description}]}
        self._data[FOF.INCOME_SPENDING].append(tax)

    def load_broker_fee(self):
        header_row = self.find_row(self.SummaryHeader) + 1
        header_found = False
        for i, row in self._statement.iterrows():
            if (not header_found) and (row[self.HeaderCol] == "Уплаченная комиссия, в том числе"):
                header_found = True  # Start of broker fees list
                continue
            if header_found:
                if row[self.HeaderCol] != "":     # End of broker fee list
                    break
                for col in range(6, self._statement.shape[1]):
                    if not self._statement[col][header_row]:
                        break
                    try:
                        fee = float(row[col])
                    except (ValueError, TypeError):
                        continue
                    if fee == 0:
                        continue
                    account_id = self._find_account_id(self._account_number, self._statement[col][header_row])
                    new_id = max([0] + [x['id'] for x in self._data[FOF.INCOME_SPENDING]]) + 1
                    fee = {"id": new_id, "timestamp": self._data[FOF.PERIOD][1], "account": account_id, "peer": 0,
                           "lines": [{"amount": fee, "category": -PredefinedCategory.Fees, "description": row[1]}]}
                    self._data[FOF.INCOME_SPENDING].append(fee)
