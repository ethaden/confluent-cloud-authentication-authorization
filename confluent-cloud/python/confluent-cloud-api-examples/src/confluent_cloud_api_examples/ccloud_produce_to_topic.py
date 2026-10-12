import datetime
import sys
import functools
import argparse
import time
import requests
import logging

from confluent_kafka import Producer, SerializingProducer
from confluent_kafka.serialization import StringSerializer
import socket

from ccloud_config import CCloud_Config
from ccloud_auth_provider_azure import AuthenticationError
from ccloud_auth_provider_base import CCloud_Auth_Provider_Base

# Acquire an Azure access token from the specified App Registration and the given scope configured in there
# Make sure that this app registration issues JWT 2.0 tokens (update its manifest!)
# Run "az login" and login to Azure with your acount (via web browser)

class CCloud_Azure_Producer:

    def __init__(self, auth_provider: CCloud_Auth_Provider_Base, env_id: str, cluster_id: str, topic: str, client_id: str=None):
        self._auth_provider = auth_provider
        self._env_id = env_id
        self._cluster_id = cluster_id
        self._topic = topic
        self._client_id = client_id

    def run(self):
        try:
            cluster_data_url = f'https://api.confluent.cloud/cmk/v2/clusters/{self._cluster_id}?environment={self._env_id}'
            headers_ccloud_api = self._auth_provider.get_auth_header(cluster_data_url)
            response = requests.get(cluster_data_url, headers=headers_ccloud_api)
            if response.status_code != 200:
                error_msg = response.json().get('errors')[0].get('detail')
                raise Exception(f'Unable to get metadata of cluster (status code: {response.status_code}, message: "{error_msg}")')
            cluster_metadata = response.json()
            cluster_name = cluster_metadata.get('spec').get('display_name')
            cluster_base_url =  cluster_metadata.get('spec').get('http_endpoint')
            kafka_bootstrap_endpoint = cluster_metadata.get('spec').get('kafka_bootstrap_endpoint')
            print (cluster_base_url)

            logger = logging.getLogger(__name__)
            string_serializer = StringSerializer('utf_8')
            client_config = {
                'bootstrap.servers': kafka_bootstrap_endpoint,
                'client.id': self._client_id or socket.gethostname(),
                'security.protocol': 'SASL_SSL',
                'sasl.mechanism': 'OAUTHBEARER',
                'oauth_cb': lambda config_str: self._auth_provider.get_azure_token_with_expiry(self._cluster_id, config_str),
                'logger': logger,
                'key.serializer': string_serializer,
                'value.serializer': string_serializer,
                'partitioner': 'murmur2'
            }
            producer = SerializingProducer(client_config)
            while True:
                producer.poll(0.0)
                now = datetime.datetime.now()
                producer.produce(self._topic, key='key', value=now.isoformat(), 
                    on_delivery = lambda err, msg: self.delivery_report(err, msg))
                time.sleep(1)
            producer.flush()

        except AuthenticationError as exc:
            print (f'Unable to authenticate: {str(exc)}')
            exit(1)
    def delivery_report(self, err, msg):
        if err is not None:
            print('Delivery failed for User record {}: {}'.format(msg.key(), err))
            return
        print('User record {} successfully produced to {} [{}] at offset {}'.format(
            msg.key(), msg.topic(), msg.partition(), msg.offset()))

if __name__ == '__main__':
    if sys.version_info >= (3, 9):
        parser = argparse.ArgumentParser(
            prog='ccloud_produce_to_topic',
            exit_on_error=True,
        )  # type: ignore  # pragma: no cover
    else:
        parser = argparse.ArgumentParser(
            prog='ccloud_produce_to_topic',
        )  # type: ignore  # pragma: no cover

    parser.add_argument('config_file', help='A config file')
    parser.add_argument('--env-id', '-e', required=True, help='The environment Id')
    parser.add_argument('--cluster-id', '-k', required=True, help='The cluster Id')
    parser.add_argument('--topic', '-t', required=True, help='The topic name')
    parser.add_argument('--client-id', '-i', help='The client ID (defaults to the config value or hostname)')
    try:
        parsed_args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        sys.exit(1)

    config = CCloud_Config(parsed_args.config_file)
    auth_provider = CCloud_Auth_Provider_Base.create_auth(config.get_auth_config())
    client_id = parsed_args.client_id or config.get_kafka_client_id() or None
    producer = CCloud_Azure_Producer(
        auth_provider,
        parsed_args.env_id,
        parsed_args.cluster_id,
        parsed_args.topic,
        client_id,
    )
    try:
        producer.run()
    except KeyboardInterrupt:
        print('Producer interrupted by user')
    except RuntimeError as exc:
        print(f'An error occurred while running the producer: {exc}')
