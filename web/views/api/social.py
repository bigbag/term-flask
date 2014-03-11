# -*- coding: utf-8 -*-
"""
    Контролер реализующий апи по взаимодействию с соцсетями

    :copyright: (c) 2014 by Denis Amelin.
    :license: BSD, see LICENSE for more details.
"""
import json
from flask import Blueprint, abort, request, make_response, url_for, render_template

from web import app, cache

from decorators.header import *
from helpers.error_xml_helper import *
from helpers import date_helper, hash_helper

from models.term_user import TermUser
from models.loyalty import Loyalty
from models.person_event import PersonEvent
from models.person import Person
from models.payment_wallet import PaymentWallet
from models.wallet_loyalty import WalletLoyalty
from models.soc_token import SocToken
from models.likes_stack import LikesStack
from models.spot import Spot

mod = Blueprint('api_social', __name__)


def api_admin_access(request):
    headers = request.headers

    if 'Key' not in headers or 'Sign' not in headers:
        abort(400)

    term_user = TermUser().get_by_api_key(headers['Key'])
    if not term_user:
        abort(403)

    true_sign = hash_helper.get_api_sign(
        str(term_user.api_secret),
        request.form)

    if not true_sign == headers['Sign']:
        abort(403)


@mod.route('/loyalty', methods=['GET'])
@xml_headers
def api_social_get_loyalties():
    """Возвращает список акций"""

    count = Loyalty.DEFAULT_COUNT
    if 'count' in request.args:
        count = int(request.args['count'])
        if count > Loyalty.MAX_COUNT:
            count = Loyalty.MAX_COUNT

    offset = 0
    if 'offset' in request.args:
        offset = int(request.args['offset'])

    api_admin_access(request)
    loyalties = Loyalty.query.filter().order_by(
        Loyalty.id)[offset:(offset + count)]

    info_xml = render_template(
        'api/social/loyalties_list.xml',
        loyalties=loyalties,
        count=count,
        offset=offset
    ).encode('cp1251')

    response = make_response(info_xml)

    return response


@mod.route('/loyalty/<int:loyalty_id>', methods=['GET'])
@xml_headers
def api_social_get_loyalty(loyalty_id):
    """Возвращает детализацию по акции"""
    api_admin_access(request)
    loyalty = Loyalty.query.get(loyalty_id)

    wl = WalletLoyalty.query.filter_by(
        loyalty_id=loyalty.id)

    walletList = []
    for part in wl:
        if part.wallet_id not in walletList:
            walletList.append(part.wallet_id)

    partWallets = PaymentWallet.query.filter(
        PaymentWallet.id.in_(walletList))

    spotList = []
    for partWallet in partWallets:
        if partWallet.discodes_id not in spotList:
            spotList.append(partWallet.discodes_id)

    spots = Spot.query.filter(Spot.discodes_id.in_(spotList))

    spotWallets = []
    for spot in spots:
        for partWallet in partWallets:
            if partWallet.discodes_id == spot.discodes_id:
                wallet = {}
                wallet['discodes_id'] = spot.discodes_id
                wallet['barcode'] = spot.barcode
                wallet['hard_id'] = partWallet.hard_id
                spotWallets.append(wallet)

    info_xml = render_template(
        'api/social/loyalty_info.xml',
        loyalty=loyalty,
        spots=spotWallets
    ).encode('cp1251')

    response = make_response(info_xml)

    return response