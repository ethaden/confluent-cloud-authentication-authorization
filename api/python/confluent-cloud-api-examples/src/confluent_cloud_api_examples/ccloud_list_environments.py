import sys
import time
import argparse
import requests
from typing import Dict, Any

from ccloud_config import CCloud_Config
from ccloud_auth_provider_azure import CCloud_Auth_Provider_Azure, AuthenticationError
from ccloud_auth_provider_base import CCloud_Auth_Provider_Base

# Acquire an Azure access token from the specified App Registration and the given scope configured in there
# Make sure that this app registration issues JWT 2.0 tokens (update its manifest!)
# Run "az login" and login to Azure with your acount (via web browser)

class CCloud_Azure_Environment_Lister:

    def __init__(self, auth_provider: CCloud_Auth_Provider_Base):
        self._auth_provider = auth_provider

    def run(self):
        try:
            initial_url = 'https://api.confluent.cloud/org/v2/environments?page_size=10'
            current_url = initial_url
            # Traverse all result pages, starting with initial one
            print ('Found the following environments:')
            while current_url is not None:
                headers_ccloud_api = self._auth_provider.get_auth_header(current_url)
                response = requests.get(current_url, headers=headers_ccloud_api)
                current_url = None
                if response.status_code != 200:
                    error_msg = response.json().get('errors')[0].get('detail')
                    raise Exception(f'Unable to list environments (status code: {response.status_code}, message: "{error_msg}")')
                response_json = response.json()
                metadata = response_json.get('metadata', None)
                if metadata is not None:
                    current_url = metadata.get('next', None)
                environments = response_json['data']
                for environment in environments:
                    print (f'{environment["display_name"]} ({environment["id"]})')
                # Potenially wait for seconds specified by server until sending next request
                rate_limit_reset_secs = int(response.headers.get('Retry-After', '0'))
                time.sleep(rate_limit_reset_secs)
        except AuthenticationError as exc:
            print (f'Unable to authenticate: {str(exc)}')
            exit(1)

if __name__=='__main__':
    if sys.version_info >= (3, 9):
        parser = argparse.ArgumentParser(prog='ccloud_list_environments',
            exit_on_error=False) # type: ignore  # pragma: no cover
    else:
        parser = argparse.ArgumentParser(prog='ccloud_list_environments') # type: ignore  # pragma: no cover
    #parser.add_argument('--exclude-managed-identity-credential', '-m', help='Disables using the managed identity in Azure authentication which might speed up the login on developer machines. Default: False', action='store_true')
    #parser.add_argument('--debug-azure-authentication', '-d', help='Log debug output from Azure authentication. Default: False', action='store_true')
    parser.add_argument('config_file', help='A config file')
    parsed_args = parser.parse_args()
    config_file_name = parsed_args.config_file
    if config_file_name is None or config_file_name=="":
        print ('Please provide a config file')
        sys.exit(1)
    config = CCloud_Config(config_file_name)
    #debug_azure_authentication = config.get('debug_azure_authentication', debug_azure_authentication)
    auth_provider = CCloud_Auth_Provider_Base.create_auth(config.get_auth_config())
    #CCloud_Auth_Provider_Azure(app_id, pool_id, exclude_managed_identity_credential=exclude_managed_identity_credential, logging_enable=debug_azure_authentication)
    env_lister = CCloud_Azure_Environment_Lister(auth_provider)
    env_lister.run()
