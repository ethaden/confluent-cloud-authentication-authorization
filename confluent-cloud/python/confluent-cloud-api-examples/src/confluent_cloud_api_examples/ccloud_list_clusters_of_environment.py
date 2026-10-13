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

class CCloud_Azure_Cluster_Lister:

    def __init__(self, auth_provider: CCloud_Auth_Provider, env_id: str ):
        self._auth_provider = auth_provider
        self._env_id = env_id

    def get_clusters(self, env_id: str)->List[str]:
        initial_url = 'https://api.confluent.cloud/org/v2/environments'
        params = {"environment": env_id}
        results = CCloud_Util.request_with_paging(initial_url, auth_provider=self._auth_provider, params=params, page_size=10)
        return results

    def run(self):
        clusters = self.get_clusters(self._env_id)
        for cluster in clusters:
            print (f'{cluster["display_name"]} ({cluster["id"]})')

if __name__ == '__main__':
    if sys.version_info >= (3, 9):
        parser = argparse.ArgumentParser(
            prog='ccloud_list_clusters_of_environment',
            exit_on_error=True,
        )  # type: ignore  # pragma: no cover
    else:
        parser = argparse.ArgumentParser(
            prog='ccloud_list_clusters_of_environment',
        )  # type: ignore  # pragma: no cover

    parser.add_argument('config_file', nargs='?', help='A config file')
    parser.add_argument('--env-id', '-e', required=True, help='The environment Id')
    try:
        parsed_args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        sys.exit(1)
    config_file_name = parsed_args.config_file
    if config_file_name is None or config_file_name=="":
        print ('Please provide a config file')
        parser.print_help()
        sys.exit(1)

    config = CCloud_Config(config_file_name)
    auth_provider = CCloud_Auth_Provider.create_auth(config.get_auth_config())
    cluster_lister = CCloud_Azure_Cluster_Lister(auth_provider, parsed_args.env_id)
    try:
        cluster_lister.run()
    except AuthenticationError as exc:
        print (f'Unable to authenticate: {str(exc)}')
        exit(1)
    except RuntimeError as exc:
        print (f'Error occurred: {str(exc)}')
        exit(1)
