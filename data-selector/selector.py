from flask import Flask, jsonify, request, url_for
from flask_api import FlaskAPI, status, exceptions
import json
import requests
import pandas as pd
import schedule
import time
import pika
import threading
from flask import Response

app = Flask(__name__)


class DataSelector:

    def start(self):
        print("Connecting exchange")
        self.credentials = pika.PlainCredentials("guest", "guest")
        self.connection_params = pika.ConnectionParameters(
         host="rabbitmq-service", credentials=self.credentials)
         #host="localhost", virtual_host="/", credentials=self.credentials)
        self.connection = pika.BlockingConnection(self.connection_params)
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='')
        queue_name = result.method.queue
        self.channel.queue_bind(exchange='data-exchange',
                                queue=queue_name)
        self.channel.basic_consume(queue=queue_name,
                                   auto_ack=False,
                                   on_message_callback=self.save)
        self.initialized = True
        self.channel.start_consuming()

    def save(self, ch, method, properties, body):
        text = body.decode('utf8')
        print("Received message")
        data = json.loads(text)

        data = pd.DataFrame.from_dict(data["records"], orient='columns')
        data.to_json("/tmp/covid-data-selector.json", orient="records")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return


@app.route('/bycountry', methods=['GET', 'POST'])
def get_data():
    country = request.args["country"]

    if country:
        with open("/tmp/covid-data-selector.json") as json_file:
            text = json_file.read()
            data = json.loads(text)
            data = pd.DataFrame.from_dict(data, orient='columns')
            data = data[data["countriesAndTerritories"] == country]
            data.sort_values(by=["year", "month", "day"], inplace=True)
            return Response(data.to_json(orient="records"), mimetype='application/json')
    return Response("{}", mimetype='application/json')


@app.route('/graphbycountry', methods=['GET', 'POST'])
def get_graph():
    country = request.args["country"]

    if country:
        with open("/tmp/covid-data-selector.json") as json_file:
            text = json_file.read()
            data = json.loads(text)
            data = pd.DataFrame.from_dict(data, orient='columns')
            data = data[data["countriesAndTerritories"] == country]
            data.sort_values(by=["year", "month", "day"], inplace=True)
            out = dict()
            out["labels"] = data["dateRep"].tolist()
            out["data"] = data["cases"].fillna(0).tolist()

            return Response(json.dumps(out), mimetype='application/json')
    return Response("{}", mimetype='application/json')


@app.route('/health', methods=['GET', 'POST'])
def health():
    if selector.connection and selector.connection.is_open and selector.initialized:
        return Response(status=200)
    Response(status=503)


selector = DataSelector()


def start_consumer():
    selector.start()
    return


if __name__ == '__main__':
    consumer_thread = threading.Thread(target=start_consumer,daemon=True)
    consumer_thread.start()
    app.run(host='0.0.0.0', port=4000, debug=False)
