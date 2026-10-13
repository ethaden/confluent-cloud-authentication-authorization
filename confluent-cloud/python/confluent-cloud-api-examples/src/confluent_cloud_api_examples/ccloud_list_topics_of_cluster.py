import sys
import time
import argparse
from confluent_cloud_api_examples.ccloud_util import CCloud_Util
import requests
from typing import Dict, Any, List

from ccloud_config import CCloud_Config
from ccloud_auth_provider_azure import AuthenticationError
from ccloud_auth_provider import CCloud_Auth_Provider

# Acquire an Azure access token from the specified App Registration and the given scope configured in there
# Make sure that this app registration issues JWT 2.0 tokens (update its manifest!)
# Run "az login" and login to Azure with your acount (via web browser)

class CCloud_Azure_Cluster_Topics:

    def __init__(self, auth_provider: CCloud_Auth_Provider, env_id: str, cluster_id: str):
        self._auth_provider = auth_provider
        self._env_id = env_id
        self._cluster_id = cluster_id

    def run(self):
        cluster_data_url = f'https://api.confluent.cloud/cmk/v2/clusters/{self._cluster_id}?environment={self._env_id}'
        headers_ccloud_api = self._auth_provider.get_auth_header(cluster_data_url)
        response = requests.get(cluster_data_url, headers=headers_ccloud_api)
        if response.status_code != 200:
            error_msg = response.json().get('errors')[0].get('detail')
            raise RuntimeError(f'Unable to get metadata of cluster (status code: {response.status_code}, message: "{error_msg}")')
        cluster_metadata = response.json()
        cluster_name = cluster_metadata.get('spec').get('display_name')
        cluster_base_url =  cluster_metadata.get('spec').get('http_endpoint')
        print (f'Found the following topics in cluster "{cluster_name}":')
        topics = self.get_topics_of_cluster(cluster_base_url, self._cluster_id)
        for topic in topics:
            print (f'{topic["topic_name"]}')

    def get_topics_of_cluster(self, cluster_base_url: str, cluster_id: str)->List[str]:
        return CCloud_Util.request_with_paging(
            url=f'{cluster_base_url}/kafka/v3/clusters/{cluster_id}/topics',
            auth_provider = self._auth_provider,
            params = { 'cluster_id': self._cluster_id }
        )

if __name__ == '__main__':
    if sys.version_info >= (3, 9):
        parser = argparse.ArgumentParser(
            prog='ccloud_list_topics_of_cluster',
            exit_on_error=True,
        )  # type: ignore  # pragma: no cover
    else:
        parser = argparse.ArgumentParser(
            prog='ccloud_list_topics_of_cluster',
        )  # type: ignore  # pragma: no cover

    parser.add_argument('config_file', help='A config file')
    parser.add_argument('--env-id', '-e', required=True, help='The environment Id')
    parser.add_argument('--cluster-id', '-k', required=True, help='The cluster Id')
    try:
        parsed_args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        sys.exit(1)

    config = CCloud_Config(parsed_args.config_file)
    auth_provider = CCloud_Auth_Provider.create_auth(config.get_auth_config())
    topic_lister = CCloud_Azure_Cluster_Topics(
        auth_provider,
        parsed_args.env_id,
        parsed_args.cluster_id,
    )
    try:
        topic_lister.run()
    except AuthenticationError as exc:
        print (f'Unable to authenticate: {str(exc)}')
        exit(1)
    except RuntimeError as exc:
        print (f'Error occurred: {str(exc)}')
        exit(1)
