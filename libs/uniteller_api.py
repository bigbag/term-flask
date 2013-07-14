# -*- coding: utf-8 -*-
"""
    Библиотека для работы с сервисом Uniteller

    :copyright: (c) 2013 by Pavel Lyashkov.
    :license: BSD, see LICENSE for more details.
"""
import hashlib
import string
from console import app
from grab import Grab
from lxml import etree


class UnitellerApi(object):
    EMPTY_ORDER = dict(
        order_id='',
        amount='',
        mean_type='',
        money_type='',
        life_time='',
        customer_id='',
        card_id='',
        l_data='',
        paymen_type='',
    )

    def __init__(self, const):
        self.const = const
        self.shop_id = self.const.SHOP_ID
        self.password = self.const.PASSWORD
        self.login = self.const.LOGIN
        self.prefix = self.const.TEST and self.const.TEST_PREFIX or self.const.DEFAULT_PREFIX

    def __repr__(self):
        return "%s" % self.const

    def get_payment_url(self):
        return "%s%s" % (self.prefix, self.const.PAYMENT_URL)

    def get_result_url(self):
        return "%s%s" % (self.prefix, self.const.RESULT_URL)

    def get_unblock_url(self):
        return "%s%s" % (self.prefix, self.const.UNBLOCK_URL)

    def get_recurrent_url(self):
        return "%s%s" % (self.prefix, self.const.RECURRENT_URL)

    def get_sing(self, order):
        result = [hashlib.md5(str(value)).hexdigest() for value in order]

        return string.upper(hashlib.md5(str('&'.join(result))).hexdigest())

    def get_recurrent_sing(self, order):
        data = (
            self.shop_id,
            order['order_id'],
            order['amount'],
            order['parent_order_id'],
            self.password)

        return self.get_sing(data)

    def get_payment_sing(self, order):
        full_order = dict(self.EMPTY_ORDER, **order)
        data = (
            self.shop_id,
            full_order['order_id'],
            full_order['amount'],
            full_order['mean_type'],
            full_order['money_type'],
            full_order['life_time'],
            full_order['customer_id'],
            full_order['card_id'],
            full_order['l_data'],
            full_order['paymen_type'],
            self.password)

        return self.get_sing(data)

    def set_request(self, url, data=None):
        return_data = False
        grab = Grab()
        if data:
            grab.setup(post=data)

        try:
            grab.go(url)
        except Exception as e:
            app.logger.error(e)
        else:
            return_data = grab

        return return_data

    def get_payment_info(self, order_id):
        return_data = False

        keys = (
            'response_code',
            'total',
            'currency',
            'date',
            'billnumber',
            'status',
            'cardnumber',
            'phone',
            'ipaddress',
        )
        data = dict(
            ShopOrderNumber=order_id,
            Shop_ID=self.shop_id,
            Login=self.login,
            Password=self.password,
            Format=4
        )

        result = self.set_request(self.get_result_url(), data)

        if result:
            try:
                tree = etree.fromstring(result.response.body)
            except Exception as e:
                app.logger.error(e)
            else:
                event_nodes = tree.xpath(
                    '/unitellerresult/orders/order')

                return_data = {}
                try:
                    for key in keys:
                        return_data[key] = event_nodes[0].find(key).text
                except Exception as e:
                    app.logger.error(e)

        return return_data
