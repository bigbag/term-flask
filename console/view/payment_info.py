# -*- coding: utf-8 -*-
"""
    Консольное приложение для получения информации об операциях с ПС

    :copyright: (c) 2013 by Pavel Lyashkov.
    :license: BSD, see LICENSE for more details.
"""
import time
from datetime import datetime
from datetime import timedelta

from flask.ext.script import Command
from console import app
from console.configs.payment import UnitellerConfig

from libs.uniteller_api import UnitellerApi
from web.models.payment_history import PaymentHistory
from web.models.payment_log import PaymentLog
from web.models.payment_wallet import PaymentWallet


class PaymentInfo(Command):

    "Return payment info"

    def set_new_payment_info(self):
        date_start = datetime.utcnow() - timedelta(days=1)
        date_stop = datetime.utcnow() - timedelta(minutes=1)

        payment_history = PaymentHistory.query.filter(
            (PaymentHistory.type == PaymentHistory.TYPE_PLUS) &
            (PaymentHistory.status == PaymentHistory.STATUS_NEW) &
            (PaymentHistory.creation_date >= date_start) &
            (PaymentHistory.creation_date < date_stop)
        ).all()

        un = UnitellerApi(UnitellerConfig)
        un.success = UnitellerApi.SUCCESS_ALL
        info = un.get_payment_info()

        for history in payment_history:
            if not str(history.id) in info:
                continue

            payment_info = info[str(history.id)]

            if payment_info['status'] == UnitellerApi.STATUS_COMPLETE:

                history.status = PaymentHistory.STATUS_COMPLETE
                if not history.save():
                    continue

                log = PaymentLog.query.get(history.id)
                if log:
                    continue

                log = PaymentLog()
                log.history_id = history.id
                log.creation_date = history.creation_date
                log.wallet_id = history.wallet_id
                log.rrn = payment_info['billnumber']
                log.card_pan = payment_info['cardnumber']
                log.save()

                wallet = PaymentWallet.query.get(history.wallet_id)
                wallet.balance = int(wallet.balance) + int(history.amount)
                wallet.save()
            else:
                history.status = PaymentHistory.STATUS_FAILURE
                history.save()

    def set_missing_payment_info(self):
        date_start = datetime.utcnow() - timedelta(days=1)
        date_stop = datetime.utcnow() - timedelta(minutes=15)

        payment_history = PaymentHistory.query.filter(
            (PaymentHistory.type == PaymentHistory.TYPE_PLUS) &
            (PaymentHistory.status == PaymentHistory.STATUS_NEW) &
            (PaymentHistory.creation_date >= date_start) &
            (PaymentHistory.creation_date < date_stop)
        ).all()

        un = UnitellerApi(UnitellerConfig)
        un.success = UnitellerApi.SUCCESS_ALL
        info = un.get_payment_info()

        for history in payment_history:
            if not str(history.id) in info:
                history.status = PaymentHistory.STATUS_MISSING
                history.save()

    def run(self):
        try:
            self.set_new_payment_info()
            self.set_missing_payment_info()
        except Exception as e:
            app.logger.error(e)
