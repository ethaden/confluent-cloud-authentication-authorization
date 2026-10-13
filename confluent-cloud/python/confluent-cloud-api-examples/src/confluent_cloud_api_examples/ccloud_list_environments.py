import sys
import time
import argparse
from confluent_cloud_api_examples.ccloud_util import CCloud_Util
import requests
from typing import Dict, Any, List

from ccloud_config import CCloud_Config
from ccloud_auth_provider_azure import CCloud_Auth_Provider_Azure, AuthenticationError
from ccloud_auth_provider import CCloud_Auth_Provider

# Acquire an Azure access token from the specified App Registration and the given scope configured in there
# Make sure that this app registration issues JWT 2.0 tokens (update its manifest!)
# Run "az login" and login to Azure with your acount (via web browser)

class CCloud_Azure_Environment_Lister:

    def __init__(self, auth_provider: CCloud_Auth_Provider):
        self._auth_provider = auth_provider

    def get_environments(self)->List[str]:
        initial_url = 'https://api.confluent.cloud/org/v2/environments'
        results = CCloud_Util.request_with_paging(initial_url, auth_provider=self._auth_provider, page_size=10)
        return results

    def run(self):
        print ('Found the following environments:')
        for environment in self.get_environments():
            print (f'{environment["display_name"]} ({environment["id"]})')

if __name__=='__main__':
    if sys.version_info >= (3, 9):
        parser = argparse.ArgumentParser(prog='ccloud_list_environments',
            exit_on_error=True) # type: ignore  # pragma: no cover
    else:
        parser = argparse.ArgumentParser(prog='ccloud_list_environments') # type: ignore  # pragma: no cover
    #parser.add_argument('--exclude-managed-identity-credential', '-m', help='Disables using the managed identity in Azure authentication which might speed up the login on developer machines. Default: False', action='store_true')
    #parser.add_argument('--debug-azure-authentication', '-d', help='Log debug output from Azure authentication. Default: False', action='store_true')
    parser.add_argument('config_file', help='A config file')
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
    #debug_azure_authentication = config.get('debug_azure_authentication', debug_azure_authentication)
    auth_provider = CCloud_Auth_Provider.create_auth(config.get_auth_config())
    #CCloud_Auth_Provider_Azure(app_id, pool_id, exclude_managed_identity_credential=exclude_managed_identity_credential, logging_enable=debug_azure_authentication)
    env_lister = CCloud_Azure_Environment_Lister(auth_provider)
    try:
        env_lister.run()
    except AuthenticationError as exc:
        print (f'Unable to authenticate: {str(exc)}')
        sys.exit(1)
    except RuntimeError as exc:
        print (f'Error occurred: {str(exc)}')
        sys.exit(1)
