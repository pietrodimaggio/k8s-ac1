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
import datetime
app = Flask(__name__)


class DataTransformer:

    def init(self):
        print("Connecting exchange")
        self.credentials = pika.PlainCredentials("guest", "guest")
        self.connection_params = pika.ConnectionParameters(
            host="rabbitmq-service", credentials=self.credentials)
        # host="localhost", virtual_host="/", credentials=self.credentials)
        self.connection = pika.BlockingConnection(self.connection_params)
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='')
        queue_name = result.method.queue
        self.channel.queue_bind(exchange='data-exchange',
                                queue=queue_name)
        self.channel.basic_consume(queue=queue_name,
                                   auto_ack=False,
                                   on_message_callback=self.transform)
        self.initialized=True
        self.channel.start_consuming()

    def transform(self, ch, method, properties, body):
        text = body.decode('utf8')
        print("Received message " + str(datetime.datetime.now()))
        data = json.loads(text)

        data = pd.DataFrame.from_dict(data["records"], orient='columns')
        population = data[["countriesAndTerritories", "popData2019"]].drop_duplicates()
        data = data[["countriesAndTerritories", "cases", "deaths"]]
        data = data.groupby(by="countriesAndTerritories").sum()
        data = data.merge(population, on="countriesAndTerritories")
        data["cases_rate"] = data["cases"] * 100000 / data["popData2019"]
        data["deaths_rate"] = data["deaths"] * 100000 / data["popData2019"]
        assert isinstance(data, pd.DataFrame)
        data.sort_values(by="cases", inplace=True, ascending=False)
        data.to_json("/tmp/covid-world.json", orient="records")

        out = dict()
        out["labels"] = data["countriesAndTerritories"].tolist()
        out["data"] = data["cases_rate"].fillna(0).tolist()
        with open("/tmp/covid-graph1.json", "w+") as outfile:
            json.dump(out, outfile)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        return


@app.route('/health', methods=['GET', 'POST'])
def health():
    if transformer.connection and transformer.connection.is_open and transformer.initialized:
        return Response(status=200)
    Response(status=503)


transformer = DataTransformer()


def start_consumer():
    transformer.init()


@app.route('/data', methods=['GET', 'POST'])
def get_data():
    with open("/tmp/covid-world.json") as json_file:
        data = json_file.read()
        return Response(data, mimetype='application/json')
    return "{}"


@app.route('/graph', methods=['GET', 'POST'])
def get_graph():
    with open("/tmp/covid-graph1.json") as json_file:
        data = json_file.read()
        return Response(data, mimetype='application/json')
    return "{}"


if __name__ == '__main__':
    consumer_thread = threading.Thread(target=start_consumer)
    consumer_thread.start()
    app.run(host='0.0.0.0', port=4000, debug=False)
