# -*- coding: utf-8 -*-
"""
    Задачи связанные с платежами

    :copyright: (c) 2014 by Pavel Lyashkov.
    :license: BSD, see LICENSE for more details.
"""
import logging

from web.celery import celery
from yandex_money.api import Wallet, ExternalPayment

from configs.general import Config

from configs.yandex import YandexMoneyConfig

from helpers import date_helper

from models.payment_history import PaymentHistory
from models.payment_card import PaymentCard
from models.payment_wallet import PaymentWallet
from models.payment_fail import PaymentFail
from models.term import Term
from models.firm import Firm
from models.report import Report


class PaymentTask(object):

    @staticmethod
    def get_fail_algorithm(algorithm):

        def condition_generator(interval, start_interval, start, count):
            condition = [dict(count=i + start, delta=i * interval + start_interval)
                         for i in xrange(1, 1 + count)]

            return dict(condition=condition, start=start + count)

        result = []
        start = 0
        start_interval = 5 * 60
        for row in algorithm:
            if 'start_interval' in row:
                start_interval = row['start_interval']

            condition = condition_generator(
                row['interval'], start_interval, start, row['count'])
            result += condition['condition']
            start = condition['start']

        result.sort(reverse=True)

        return result

    @staticmethod
    def set_fail(report_id, wallet):
        PaymentFail.add_or_update(report_id)
        wallet.add_to_blacklist()

    @staticmethod
    def set_success(report_id, wallet):
        payment = PaymentFail.query.get(report_id)
        if payment:
            payment.delete()
        wallet.remove_from_blacklist()

    @staticmethod
    @celery.task
    def payment_manager():
        PaymentTask.new_payment_manager.delay()
        PaymentTask.fail_payment_manager.delay()

    @staticmethod
    @celery.task
    def fail_payment_manager():
        payments = PaymentFail.query.all()
        if not payments:
            return False

        algorithm = PaymentTask.get_fail_algorithm(Config.FAIL_PAYMENT_ALGORITHM)
        for payment in payments:
            delta = date_helper.get_curent_utc() - payment.timestamp
            for row in algorithm:
                if payment.count != row['count']:
                    continue

                if delta < row['delta']:
                    continue

                PaymentFail.add_or_update(payment.report_id)
                payment_task = PaymentTask()
                PaymentTask.background_payment.delay(payment_task,
                                                     payment.report_id)

    @staticmethod
    @celery.task
    def new_payment_manager():
        reports = Report.get_new_payment()
        if not reports:
            return False

        for report in reports:
            history = PaymentHistory.query.filter_by(
                report_id=report.id).first()
            if history:
                continue

            payment_task = PaymentTask()
            # Start: Костыль на время перехода от кошельков с балансом
            wallet = PaymentWallet.get_valid_by_payment_id(report.payment_id)
            if wallet and int(wallet.balance) > 0:
                PaymentTask.background_old_payment.delay(payment_task,
                                                         report.id)
                continue
            # End
            PaymentTask.background_payment.delay(payment_task, report.id)

        history = PaymentHistory.get_new_payment()
        for key in history:
            PaymentTask.check_status.delay(key.id)

        return True

    @staticmethod
    @celery.task
    def check_status(history_id):
        log = logging.getLogger('payment')

        history = PaymentHistory.query.get(history_id)
        if not history:
            message = 'Check: Not found history, history_id=%s' % history_id
            log.error(message)
            return message

        wallet = PaymentWallet.query.get(history.wallet_id)
        if not wallet:
            message = 'Check: Not found wallet, wallet_id=%s' % wallet.id
            log.error(message)
            return message

        card = PaymentCard.get_payment_card(history.wallet_id)
        if not card:
            message = 'Payment: Not found card, for history_id=%s' % history.id
            log.error(message)
            return False

        try:
            request_options = {"request_id": history.request_id}
            if card.system == PaymentCard.SYSTEM_MPS:
                ym = ExternalPayment(YandexMoneyConfig.INSTANCE_ID)
                result = ym.process(request_options)
            elif card.system == PaymentCard.SYSTEM_YANDEX:
                ym = Wallet(card.token)
                result = ym.process_payment(request_options)
            else:
                return False
        except Exception as e:
            log.error(e)
            return False
        else:
            if not result or 'status' not in result:
                PaymentTask.set_fail(history.report_id, wallet)
                history.delete()
                message = 'Check: Fail, report_id=%s, request_id=%s' % \
                    (history.report_id, history.request_id)
                log.error(message)
                log.error(result)
                return message

            if result['status'] in ('refused', 'ext_auth_required'):
                PaymentTask.set_fail(history.report_id, wallet)
                history.delete()
                message = 'Check: Fail, report_id=%s, request_id=%s' % \
                    (history.report_id, history.request_id)
                log.error(message)
                log.error(result)
                return message

            if result['status'] == 'in_progress':
                history.status = PaymentHistory.STATUS_IN_PROGRESS
                history.save()

            elif result['status'] == 'success':
                if not 'invoice_id' in result:
                    message = 'Check: Fail, not found invoice_id, history_id=%s' % history_id
                    log.error(message)
                    log.error(result)
                    return message

                history.invoice_id = result['invoice_id']
                history.status = PaymentHistory.STATUS_COMPLETE
                history.save()

                PaymentTask.set_success(history.report_id, wallet)

                report = Report.query.get(history.report_id)
                report.status = Report.STATUS_COMPLETE
                report.save()

            return True

    def check_payment_data(self, report_id):
        """Проверяем входные данные"""
        log = logging.getLogger('payment')

        self.report = Report.query.get(report_id)
        if not self.report:
            message = 'Payment: Not found report with id %s' % report_id
            log.error(message)
            return message

        self.wallet = PaymentWallet.get_by_payment_id(self.report.payment_id)
        if not self.wallet:
            message = 'Payment: Not found wallet with pid %s' % self.report.payment_id
            log.error(message)
            return message

        self.history = PaymentHistory.query.filter_by(report_id=self.report.id).first()
        if self.history:
            return False

    @celery.task
    def background_payment(self, report_id):
        """Проводим фоновый платеж"""
        log = logging.getLogger('payment')

        self.check_payment_data(report_id)

        history = PaymentHistory().from_report(self.report, self.wallet)
        if not history:
            message = 'Payment: Fail in history add, report_id=%s' % report_id
            log.error(message)
            return message

        card = PaymentCard.get_payment_card(self.wallet.id)
        if not card:
            PaymentTask.set_fail(report_id, self.wallet)
            history.delete()
            message = 'Payment: Not found card, for wallet_id=%s' % self.wallet.id
            log.error(message)
            return False

        term = Term.query.get(self.report.term_id)
        if not term:
            log.error('Payment: Not found term %s' % self.report.term_id)

        firm = Firm.query.get(self.report.term_firm_id)
        if not firm:
            log.error(
                'Payment: Not found firm, with term %s' % self.report.term_id)

        request_options = {
            "pattern_id": firm.pattern_id,
            "sum": float(self.report.amount) / int(Term.DEFAULT_FACTOR),
            "customerNumber": history.id,
        }

        try:
            if card.system == PaymentCard.SYSTEM_MPS:
                history.system = PaymentHistory.SYSTEM_MPS
                ym = ExternalPayment(YandexMoneyConfig.INSTANCE_ID)
                payment = ym.request(request_options)
            elif card.system == PaymentCard.SYSTEM_YANDEX:
                history.system = PaymentHistory.SYSTEM_YANDEX
                ym = Wallet(card.token)
                payment = ym.request_payment(request_options)
            else:
                return False
        except Exception as e:
            log.error(e)
            return False
        else:
            if not payment or 'request_id' not in payment:
                PaymentTask.set_fail(report_id, self.wallet)
                message = 'Payment: Fail in request payment, report_id %s, request %s' % (
                    report_id, payment)
                log.error(message)
                history.delete()
                return message

            history.request_id = payment['request_id']
            history.save()
            return True

    # Start: Костыль на время перехода от кошельков с балансом
    @celery.task
    def background_old_payment(self, report_id):
        """Платеж с кошелька uniteller"""
        log = logging.getLogger('payment')

        self.check_payment_data(report_id)

        history = PaymentHistory().from_report(self.report, self.wallet)
        if not history:
            message = 'Payment: Fail in history add, report_id=%s' % report_id
            log.error(message)
            return message

        term = Term.query.get(self.report.term_id)
        if not term:
            log.error('Payment: Not found term %s' % self.report.term_id)

        new_balance = self.wallet.balance - self.report.amount

        if new_balance < 0:
            self.history.amount = self.wallet.balance
            self.wallet.balance = 0
            self.report.copy_new_from_old(new_balance)
        else:
            self.wallet.balance = new_balance

        if not self.wallet.save():
            return False

        history.request_id = 'old'
        history.status = PaymentHistory.STATUS_COMPLETE
        if not history.save():
            return False

        self.report.status = Report.STATUS_COMPLETE
        if not self.report.save():
            return False

        return True
    # End

    @staticmethod
    @celery.task
    def check_linking_manager():
        select_status = (
            PaymentHistory.STATUS_NEW,
            PaymentHistory.STATUS_IN_PROGRESS)

        all_history = PaymentHistory.query.filter(
            PaymentHistory.type == PaymentHistory.TYPE_SYSTEM).filter(
                PaymentHistory.status.in_(select_status)).all()

        for key in all_history:
            PaymentTask.check_linking.delay(key)

        return True

    @staticmethod
    @celery.task
    def check_linking(history):
        result = PaymentCard().linking_card(history.id)
        return result

    @staticmethod
    @celery.task
    def get_ym_token(discodes_id, code, url):
        log = logging.getLogger('payment')

        wallet = PaymentWallet.get_valid_by_discodes_id(discodes_id)
        if not wallet:
            return False

        try:
            info = Wallet.get_access_token(
                client_id=YandexMoneyConfig.CLIENT_ID,
                code=code,
                redirect_uri=url,
                client_secret=YandexMoneyConfig.OAUTH_KEY)
        except Exception as e:
            log.error(e)
            return False
        else:
            if 'error' in info:
                log.error(info)
                return False
            try:
                PaymentCard.set_archiv(wallet.id)

                card = PaymentCard.add_ym_wallet(wallet, info['access_token'])
                card.save()
            except Exception as e:
                log.error(e)
                return False
            else:
                wallet.blacklist = PaymentWallet.ACTIVE_ON
                wallet.save()
            return True

    @staticmethod
    @celery.task
    def ym_account_manager():
        query = PaymentCard.query.filter(
            PaymentCard.system == PaymentCard.SYSTEM_YANDEX)
        cards = query.filter(PaymentCard.pan.is_(None)).all()
        if not cards:
            return False

        for card in cards:
            PaymentTask.get_ym_account.delay(card.id)

    @staticmethod
    @celery.task
    def get_ym_account(card_id):
        log = logging.getLogger('payment')

        card = PaymentCard.query.get(card_id)
        if not card:
            message = 'Payment: Not found card card_id=%s' % card_id
            log.error(message)
            return False

        wallet = Wallet(card.token)
        try:
            info = wallet.account_info()
        except Exception as e:
            log.error(e)
            return False
        else:
            if 'account' not in info:
                return False

            card.pan = info['account']
            card.save()
            return True
