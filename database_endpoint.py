from flask import Flask, request, g
from flask_restful import Resource, Api
from sqlalchemy import create_engine, select, MetaData, Table
from flask import jsonify
import json
import eth_account
import algosdk
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import load_only

from models import Base, Order, Log
engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

app = Flask(__name__)

#These decorators allow you to use g.session to access the database inside the request code
@app.before_request
def create_session():
    g.session = scoped_session(DBSession) #g is an "application global" https://flask.palletsprojects.com/en/1.1.x/api/#application-globals

@app.teardown_appcontext
def shutdown_session(response_or_exc):
    g.session.commit()
    g.session.remove()

"""
-------- Helper methods (feel free to add your own!) -------
"""

def log_message(d):
    # Takes input dictionary d and writes it to the Log table
    message = json.dumps(d)
    g.session.add(Log(message))
    g.session.commit()
    pass

"""
---------------- Endpoints ----------------
"""
    
@app.route('/trade', methods=['POST'])
def trade():
    if request.method == "POST":
        content = request.get_json(silent=True)
        print( f"content = {json.dumps(content)}" )
        columns = [ "sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform" ]
        fields = [ "sig", "payload" ]
        error = False
        for field in fields:
            if not field in content.keys():
                print( f"{field} not received by Trade" )
                print( json.dumps(content) )
                log_message(content)
                return jsonify( False )
        
        error = False
        for column in columns:
            if not column in content['payload'].keys():
                print( f"{column} not received by Trade" )
                error = True
        if error:
            print( json.dumps(content) )
            log_message(content)
            return jsonify( False )
            
        #Your code here
        #Note that you can access the database session using g.session

        #
        # {'sig': signature,
        # 'payload': { 'sender_pk': public_key,
        #     'receiver_pk': public_key,
        #    'buy_currency': "Ethereum",
        #    'sell_currency': "Algorand",
        #    'buy_amount': 51,
        #    'sell_amount': 257,
        #    'platform': 'Algorand'
        #    }
     
        sig = content['sig'] # signature
        payload = content['payload'] # payload
        
        sender_pk = payload['sender_pk'] # payload - sender_pk
        receiver_pk = payload['receiver_pk'] # payload - receiver_pk
        buy_currency = payload['buy_currency'] # payload - buy_currency
        sell_currency = payload['sell_currency'] # payload - sell_currency
        buy_amount = payload['buy_amount'] # payload - buy_amount
        sell_amount = payload['sell_amount'] # payload - sell_amount
        platform = payload['platform'] # payload - platform
        
        # dump payload message
        payload = json.dumps(content['payload'])

        # Case 1: sig for Ethereum
        if platform == 'Ethereum':
            eth_encoded_msg = eth_account.messages.encode_defunct(text=payload)

            if eth_account.Account.recover_message(eth_encoded_msg,signature=sig) == sender_pk:
                result = True
            else:
                result = False

        # Case 2: sig for Algorand
        elif platform == 'Algorand':

            if algosdk.util.verify_bytes(payload.encode('utf-8'), sig, sender_pk):
                result = True
            else:
                result = False
        
        # Case 3: any other crypto platform
        else:
            result = False

        if result is True:
            this_order = Order(sender_pk=sender_pk, receiver_pk=receiver_pk, buy_currency=buy_currency, sell_currency=sell_currency, buy_amount=buy_amount, sell_amount=sell_amount, signature=sig)
            g.session.add(this_order)
            g.session.commit()

        return jsonify(result)



@app.route('/order_book')
def order_book():
    #Your code here
    #Note that you can access the database session using g.session
    result = {'data': []}
    for this in g.session.query(Order).all():
        result['data'].append({'sender_pk': this.sender_pk, 'receiver_pk': this.receiver_pk, 'buy_currency': this.buy_currency, 'sell_currency': this.sell_currency, 'buy_amount': this.buy_amount, 'sell_amount': this.sell_amount, 'signature': this.signature})
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(port='5002')
