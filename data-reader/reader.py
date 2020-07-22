from flask import Flask, jsonify, request, url_for
from flask_api import FlaskAPI, status, exceptions
import json
import requests
import pandas as pd
import schedule
import time
import pika
import datetime

class DataReader:

    def __init__(self):
        print("Connecting exchange")
        self.credentials = pika.PlainCredentials("guest", "guest")
        self.connection_params = pika.ConnectionParameters(
           #host="rabbitmq-service" , credentials=self.credentials)
           host="localhost", credentials=self.credentials)
        self.connection = pika.BlockingConnection(self.connection_params)
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='data-exchange',
                                 exchange_type='fanout')

    def get_data(self):
        print("Getting data " + str(datetime.datetime.now()))
        response = requests.get("https://opendata.ecdc.europa.eu/covid19/casedistribution/json/", timeout=60)
        if response.status_code == 200:
            data = response.json()
            print("Data found" + str(datetime.datetime.now()))
            self.channel.basic_publish(exchange="data-exchange", routing_key='',
                                       body=response.content)
            return

        print("No data found")




reader =  DataReader()


def job():
    reader.get_data()
    return

job()
schedule.every(60).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)