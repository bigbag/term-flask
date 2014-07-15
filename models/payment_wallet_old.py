# -*- coding: utf-8 -*-
"""
    Модель для платежной кошелька Uniteller


    :copyright: (c) 2014 by Pavel Lyashkov.
    :license: BSD, see LICENSE for more details.
"""
import hashlib
import random

from web import db

from models.base_model import BaseModel
from models.user import User

from helpers import date_helper, hash_helper


class PaymentWalletOld(db.Model, BaseModel):

    __bind_key__ = 'payment_old'
    __tablename__ = 'wallet_old'

    STATUS_NOACTIVE = 0
    STATUS_ACTIVE = 1
    STATUS_BANNED = -1

    BLACKLIST_ON = 1
    BLACKLIST_OFF = 0

    TYPE_DEMO = 0
    TYPE_FULL = 1

    BALANCE_MIN = 0

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(20), index=True)
    hard_id = db.Column(db.Integer(), index=True)
    name = db.Column(db.Integer(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')
    discodes_id = db.Column(db.Integer(), index=True)
    creation_date = db.Column(db.DateTime, nullable=False)
    balance = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    type = db.Column(db.Integer(), index=True)

    def __init__(self):
        self.discodes_id = 0
        self.name = 'My spot'
        self.type = self.TYPE_FULL
        self.balance = 0
        self.user_id = 0
        self.creation_date = date_helper.get_curent_date()
        self.status = self.STATUS_NOACTIVE

    @staticmethod
    def get_by_payment_id(payment_id):
        return PaymentWalletOld.query.filter_by(payment_id=payment_id).first()

    @staticmethod
    def get_valid_by_payment_id(payment_id):
        return PaymentWalletOld.query.filter(
            PaymentWalletOld.payment_id == payment_id).filter(
                PaymentWalletOld.status == PaymentWalletOld.STATUS_ACTIVE).filter(
                    PaymentWalletOld.user_id != 0).first()

    @staticmethod
    def get_invalid():
        query = PaymentWalletOld.query
        query = query.filter((
            PaymentWalletOld.status != PaymentWalletOld.STATUS_ACTIVE) | (PaymentWalletOld.balance <= PaymentWalletOld.BALANCE_MIN))
        return query.group_by(PaymentWalletOld.payment_id).all()

    def save(self):
        self.payment_id = str(self.payment_id).rjust(20, '0')
        return BaseModel.save(self)
