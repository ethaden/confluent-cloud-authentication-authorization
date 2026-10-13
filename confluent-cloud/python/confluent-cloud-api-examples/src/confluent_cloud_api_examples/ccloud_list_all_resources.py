import sys
import time
import argparse
from confluent_cloud_api_examples.ccloud_util import CCloud_Util
import requests
from typing import Dict, Any, List, OrderedDict

from ccloud_config import CCloud_Config
from ccloud_auth_provider_azure import AuthenticationError
from ccloud_auth_provider import CCloud_Auth_Provider

# Acquire an Azure access token from the specified App Registration and the given scope configured in there
# Make sure that this app registration issues JWT 2.0 tokens (update its manifest!)
# Run "az login" and login to Azure with your acount (via web browser)

class CCloud_All_Resource_Lister:

    def __init__(self, auth_provider: CCloud_Auth_Provider):
        self._auth_provider = auth_provider

    def get_environments(self)->OrderedDict[str, str]:
        initial_url = 'https://api.confluent.cloud/org/v2/environments'
        results = CCloud_Util.request_with_paging(initial_url, auth_provider=self._auth_provider, page_size=10)
        environments_list: OrderedDict[str, str] = OrderedDict()
        for environment in results:
            environments_list[environment["id"]] = environment["display_name"]
        return environments_list

    def get_clusters(self, env_id)->OrderedDict[str, str]:
        initial_url = f'https://api.confluent.cloud/cmk/v2/clusters'
        params = {"environment": env_id}
        results = CCloud_Util.request_with_paging(initial_url, auth_provider=self._auth_provider, params=params, page_size=10)
        all_clusters: OrderedDict[str, str] = OrderedDict()
        for result in results:
            all_clusters[result["id"]] = result["spec"]["display_name"]
        return all_clusters

    def get_schema_registry(self, env_id: str)->List[str]:
        initial_url = f'https://api.confluent.cloud/srcm/v3/clusters'
        params = {"environment": env_id}
        results = CCloud_Util.request_with_paging(initial_url, auth_provider=self._auth_provider, params=params, page_size=10)
        all_schema_registry_clusters: List[str] = []
        for result in results:
            all_schema_registry_clusters.append(result["id"])
        return all_schema_registry_clusters

    def run(self):
        environments = self.get_environments()
        print("Environments found:")
        for env_id, env_name in environments.items():
            print(f'Environment "{env_name}" ({env_id})')
            print (' Clusters:')
            for cluster_id, cluster_name in self.get_clusters(env_id).items():
                print(f'  "{cluster_name}" ({cluster_id})')
            print (' Schema Registry Cluster:')
            for sr_id in self.get_schema_registry(env_id):
                print(f'  "{sr_id}"')

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
    cluster_lister = CCloud_All_Resource_Lister(auth_provider)
    try:
        cluster_lister.run()
    except AuthenticationError as exc:
        print (f'Unable to authenticate: {str(exc)}')
        exit(1)
    except RuntimeError as exc:
        print (f'Error occurred: {str(exc)}')
        exit(1)
