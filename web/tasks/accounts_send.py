# -*- coding: utf-8 -*-
"""
    Задача генерации счета

    :copyright: (c) 2014 by Denis Amelin.
    :license: BSD, see LICENSE for more details.
"""
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from web import app
from web.celery import celery
from web.tasks import mail
from web.emails.term.account import AccountMessage

from helpers import date_helper

from models.payment_account import PaymentAccount
from models.firm import Firm
from models.report import Report


class AccountSenderTask (object):

    @staticmethod
    @celery.task
    def accounts_manager():
        firms = Firm.query.filter((Firm.transaction_percent > 0) | (Firm.transaction_comission > 0)).all()

        search_date = datetime.utcnow() - timedelta(days=20)
        
        for firm in firms:
            AccountSenderTask.account_generate.delay(firm.id, search_date)

    @staticmethod
    @celery.task
    def account_generate(firm_id, search_date):
        firm = Firm.query.get(firm_id)
        if not firm:
            return False

        interval = date_helper.get_date_interval(search_date, 'month')

        query = Report.query.filter(Report.term_firm_id == firm.id)
        query = query.filter(Report.status == Report.STATUS_COMPLETE)
        query = query.filter(
            Report.creation_date.between(interval[0], interval[1]))
        reports = query.all()

        if not len(reports):
            return False

        query = PaymentAccount.query.filter(
            PaymentAccount.firm_id == firm.id)
        query = query.filter(
            PaymentAccount.status == PaymentAccount.STATUS_GENERATED)
        query = query.filter(func.DATE(
            PaymentAccount.generated_date) == func.DATE(date_helper.get_current_date()))

        account = query.first()
        if not account:
            account = PaymentAccount()
            account.firm_id = firm.id

        account.items_count = query.count()
        account.summ = 0

        for report in reports:
            if firm.transaction_percent > 0:
                account.summ = account.summ + \
                    float(report.amount) * \
                    (float(firm.transaction_percent) / 100 / 100)
            elif firm.transaction_comission > 0:
                account.summ = account.summ + firm.transaction_comission

        account.save()
        account.filename = account.generate_pdf()

        account.save()

        emails = firm.decode_field(firm.account_email)
        for email in emails:
            mail.send.delay(
                AccountMessage,
                to=email,
                attach="%s/%s" % (app.config['PDF_FOLDER'],
                                  account.filename),
                date_text=account.get_month_year())

        return True
