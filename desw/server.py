import alchemyjsonschema as ajs
import bitjws
import copy
import json
import logging
import os
import sys
import sqlalchemy as sa
import sqlalchemy.orm as orm
from alchemyjsonschema.dictify import jsonify
from flask import Flask, request, current_app, make_response
from flask.ext.cors import CORS
from flask.ext.login import login_required, current_user
from flask_bitjws import FlaskBitjws, load_jws_from_request, FlaskUser
from jsonschema import validate, ValidationError
from sqlalchemy_login_models.model import UserKey, User as SLM_User
import plugin
from desw import CFG, models, ses, eng

ps = plugin.load_plugins()

# get the swagger spec for this server
iml = os.path.dirname(os.path.realpath(__file__))
SWAGGER_SPEC = json.loads(open(iml + '/static/swagger.json').read())
# invert definitions
def jsonify2(obj, name):
    #TODO replace this with a cached definitions patch
    #this is inefficient to do each time...
    spec = copy.copy(SWAGGER_SPEC['definitions'][name])
    spec['definitions'] = SWAGGER_SPEC['definitions']
    return jsonify(obj, spec)

__all__ = ['app', ]


def get_last_nonce(app, key, nonce):
    """
    Get the last_nonce used by the given key from the SQLAlchemy database.
    Update the last_nonce to nonce at the same time.

    :param str key: the public key the nonce belongs to
    :param int nonce: the last nonce used by this key
    """
    uk = ses.query(UserKey).filter(UserKey.key==key)\
            .filter(UserKey.last_nonce<nonce * 1000).first()
    if not uk:
        return None
    lastnonce = copy.copy(uk.last_nonce)
    # TODO Update DB record in same query as above, if possible
    uk.last_nonce = nonce * 1000
    try:
        ses.commit()
    except Exception as e:
        current_app.logger.exception(e)
        ses.rollback()
        ses.flush()
    return lastnonce


def get_user_by_key(app, key):
    """
    An SQLAlchemy User getting function. Get a user by public key.

    :param str key: the public key the user belongs to
    """
    user = ses.query(SLM_User).join(UserKey).filter(UserKey.key==key).first()
    return user

# Setup flask app and FlaskBitjws
app = Flask(__name__)
app._static_folder = "%s/static" % os.path.realpath(os.path.dirname(__file__))

FlaskBitjws(app, privkey=CFG.get('bitjws', 'PRIV_KEY'), get_last_nonce=get_last_nonce,
            get_user_by_key=get_user_by_key, basepath=CFG.get('bitjws', 'BASEPATH'))

CORS(app)


@app.route('/balance', methods=['GET'])
@login_required
def get_balance():
    """
    Get the latest balance(s) for a single User.
    Currently no search parameters are supported. All balances returned.
    ---
    responses:
      '200':
        description: the User's balance(s)
        schema:
          items:
            $ref: '#/definitions/Balance'
          type: array
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: getBalance
    """
    balsq = ses.query(models.Balance).filter(models.Balance.user_id == current_user.id)

    if not balsq:
        return None
    bals = [jsonify2(b, 'Balance') for b in balsq]
    response = current_app.bitjws.create_response(bals)
    return response


@app.route('/address', methods=['POST'])
@login_required
def create_address():
    """
    Create a new address owned by your user.
    ---
    parameters:
      - name: address
        in: body
        description: The pseudo-address you would like to create. i.e. currency and network
        required: true
        schema:
          $ref: '#/definitions/Address'
    responses:
      '200':
        description: Your new address
        schema:
          $ref: '#/definitions/Address'
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: createAddress
    """
    currency = request.jws_payload['data'].get('currency')
    network = request.jws_payload['data'].get('network')
    state = 'active'
    if network.lower() in ps:
        try:
            addy = ps[network.lower()].get_new_address()
        except Exception as e:
            print type(e)
            print e
            current_app.logger.error(e)
            return 'wallet temporarily unavailable', 500
    else:
        return 'Invalid network', 400
    address = models.Address(addy, currency, network, state, current_user.id)
    ses.add(address)
    try:
        ses.commit()
    except Exception as ie:
        ses.rollback()
        ses.flush()
        return 'Could not save address', 500
    newaddy = jsonify2(address, 'Address')
    current_app.logger.info("created new address %s" % newaddy)
    return current_app.bitjws.create_response(newaddy)


@app.route('/address', methods=['GET'])
@login_required
def get_address():
    """
    Get one or more existing address(es) owned by your user.
    ---
    parameters:
      - name: address
        in: body
        description: The address you'd like to get info about.
        required: false
        schema:
          $ref: '#/definitions/Address'
    responses:
      '200':
        description: Your new address
        schema:
          items:
              $ref: '#/definitions/Address'
          type: array
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: getAddress
    """
    address = request.jws_payload['data'].get('address')
    currency = request.jws_payload['data'].get('currency')
    network = request.jws_payload['data'].get('network')
    addysq = ses.query(models.Address).filter(models.Address.user_id == current_user.id)
    if address:
        addysq = addysq.filter(models.Address.address == address)
    elif currency:
        addysq = addysq.filter(models.Address.currency == currency)
    elif network:
        addysq = addysq.filter(models.Address.currency == network)
    if not addysq:
        return None
    addys = [jsonify2(a, 'Address') for a in addysq]
    response = current_app.bitjws.create_response(addys)
    return response


@app.route('/debit', methods=['POST'])
@login_required
def create_debit():
    """
    Create a new debit, sending tokens out of your User's account.
    ---
    parameters:
      - name: debit
        in: body
        description: The debit you would like to create.
        required: true
        schema:
          $ref: '#/definitions/Debit'
    responses:
      '200':
        description: The Debit record
        schema:
          $ref: '#/definitions/Debit'
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: sendMoney
    """
    amount = request.jws_payload['data'].get('amount')
    address = request.jws_payload['data'].get('address')
    currency = request.jws_payload['data'].get('currency')
    network = request.jws_payload['data'].get('network')
    reference = request.jws_payload['data'].get('reference')
    state = 'unconfirmed'
    fee_by_amount_to_send = False
    fee_by_balance = False
    if network.lower() not in ps:
        return 'Invalid network', 400

    dbaddy = ses.query(models.Address)\
        .filter(models.Address.address == address)\
        .filter(models.Address.currency == currency).first()
    if dbaddy is not None and dbaddy.address == address:
        network = 'internal'
    elif network == 'internal' and dbaddy is None:
        return "internal address not found", 400
    else:
        if not network == 'Mock':
            fee = float(CFG.get(network, 'FEE'))
            if fee > 0:
                fee_by_amount_to_send = CFG.get(network, 'DISCOUNT_FEE_BY') == 'amount_to_send'
                fee_by_balance = CFG.get(network, 'DISCOUNT_FEE_BY') == 'balance'

    txid = 'TBD'

    if fee_by_amount_to_send:
        amount -= (amount * fee)

    debit = models.Debit(
        amount, address, currency,
        network, state, reference, txid, current_user.id)
    ses.add(debit)

    bal = ses.query(models.Balance)\
        .filter(models.Balance.user_id == current_user.id)\
        .filter(models.Balance.currency == currency)\
        .order_by(models.Balance.time.desc()).first()

    amount_with_fee = amount + (amount * fee) if \
        fee_by_balance else amount

    if not bal or bal.available < amount_with_fee:
        return "not enough funds", 400
    else:
        bal.total -= amount_with_fee
        bal.available -= amount_with_fee
        ses.add(bal)
        current_app.logger.info("updating balance %s" % jsonify2(bal, 'Balance'))
    try:
        ses.commit()
    except Exception as ie:
        current_app.logger.exception(ie)
        ses.rollback()
        ses.flush()
        return "unable to send funds", 500

    if network == 'internal':
        bal2 = ses.query(models.Balance)\
            .filter(models.Balance.user_id == dbaddy.user_id)\
            .filter(models.Balance.currency == currency)\
            .order_by(models.Balance.time.desc()).first()
        bal2.available += amount
        bal2.total += amount
        credit = models.Credit(amount, address, currency, network, 'complete', reference, debit.id, dbaddy.user_id)
        ses.add(bal2)
        ses.add(credit)
        current_app.logger.info("updating balance %s" % jsonify2(bal2, 'Balance'))
        current_app.logger.info("created new credit %s" % jsonify2(credit, 'Credit'))
        try:
            ses.commit()
            debit.ref_id = str(credit.id)
        except Exception as ie:
            ses.rollback()
            ses.flush()
            return "unable to send funds", 500
    else:
        try:
            debit.ref_id = ps[network.lower()].send_to_address(address, float(amount) / 1e8)
        except Exception as e:
            print type(e)
            print e
            current_app.logger.error(e)
            return 'wallet temporarily unavailable', 500

    debit.state = 'complete'
    try:
        ses.commit()
    except Exception as ie:
        current_app.logger.exception(ie)
        ses.rollback()
        ses.flush()
        return "Sent but unconfirmed... check again soon", 200

    result = jsonify2(debit, 'Debit')
    current_app.logger.info("created new debit %s" % result)
    return current_app.bitjws.create_response(result)


@app.route('/user', methods=['GET'])
@login_required
def get_user():
    """
    Get your user object.

    Users may only get their own info, not others'.
    ---
    responses:
      '200':
        description: user response
        schema:
          $ref: '#/definitions/User'
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    description: get your user record
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: getUserList
    """
    userdict = jsonify2(current_user.db_user, 'User')
    return current_app.bitjws.create_response(userdict)


@app.route('/user', methods=['POST'])
def add_user():
    """
    Register a new User.
    Create a User and a UserKey based on the JWS header and payload.
    ---
    operationId:
      addUser
    parameters:
      - name: user
        in: body
        description: A new User to add
        required: true
        schema:
          $ref: '#/definitions/User'
    responses:
      '200':
        description: "user's new key"
        schema:
          $ref: '#/definitions/UserKey'
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    """
    load_jws_from_request(request)
    if not hasattr(request, 'jws_header') or request.jws_header is None:
        return "Invalid Payload", 401
    username = request.jws_payload['data'].get('username')
    address = request.jws_header['kid']
    user = SLM_User(username=username)
    ses.add(user)
    try:
        ses.commit()
    except Exception as ie:
        current_app.logger.exception(ie)
        ses.rollback()
        ses.flush()
        return 'username taken', 400
    userkey = UserKey(key=address, keytype='public', user_id=user.id,
                      last_nonce=request.jws_payload['iat']*1000)
    ses.add(userkey)
    for plug in ps:
        ses.add(models.Balance(total=0, available=0, currency=ps[plug].CURRENCY, reference='open account', user_id=user.id))
    try:
        ses.commit()
    except Exception as ie:
        current_app.logger.exception(ie)
        ses.rollback()
        ses.flush()
        #ses.delete(user)
        #ses.commit()
        return 'username taken', 400
    jresult = jsonify2(userkey, 'UserKey')
    current_app.logger.info("registered user %s with key %s" % (user.id, userkey.key))

    return current_app.bitjws.create_response(jresult)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8002, debug=True)
    
