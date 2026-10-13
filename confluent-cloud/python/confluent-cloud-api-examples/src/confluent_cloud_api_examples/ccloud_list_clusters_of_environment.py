import sys
import time
import argparse
import requests
from typing import Dict, Any

from ccloud_config import CCloud_Config
from ccloud_auth_provider_azure import AuthenticationError
from ccloud_auth_provider_base import CCloud_Auth_Provider_Base

# Acquire an Azure access token from the specified App Registration and the given scope configured in there
# Make sure that this app registration issues JWT 2.0 tokens (update its manifest!)
# Run "az login" and login to Azure with your acount (via web browser)

class CCloud_Azure_Cluster_Lister:

    def __init__(self, auth_provider: CCloud_Auth_Provider_Base, env_id: str ):
        self._auth_provider = auth_provider
        self._env_id = env_id

    def run(self):
        initial_url = f'https://api.confluent.cloud/cmk/v2/clusters?environment={self._env_id}&page_size=10'
        current_url = initial_url
        # Traverse all result pages, starting with initial one
        print ('Found the following clusters:')
        while current_url is not None:
            headers_ccloud_api = self._auth_provider.get_auth_header(current_url)
            response = requests.get(current_url, headers=headers_ccloud_api)
            current_url = None
            if response.status_code != 200:
                error_msg = response.json().get('errors')[0].get('detail')
                raise RuntimeError(f'Unable to list clusters (status code: {response.status_code}, message: "{error_msg}")')
            response_json = response.json()
            metadata = response_json.get('metadata', None)
            if metadata is not None:
                current_url = metadata.get('next', None)
            clusters = response_json['data']
            if clusters is None:
                break
            for cluster in clusters:
                print (f'{cluster["spec"]["display_name"]} ({cluster["id"]})')
            # Potenially wait for seconds specified by server until sending next request
            rate_limit_reset_secs = int(response.headers.get('Retry-After', '0'))
            time.sleep(rate_limit_reset_secs)

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
    auth_provider = CCloud_Auth_Provider_Base.create_auth(config.get_auth_config())
    cluster_lister = CCloud_Azure_Cluster_Lister(auth_provider, parsed_args.env_id)
    try:
        cluster_lister.run()
    except AuthenticationError as exc:
        print (f'Unable to authenticate: {str(exc)}')
        exit(1)
    except RuntimeError as exc:
        print (f'Error occurred: {str(exc)}')
        exit(1)
