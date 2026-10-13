import time
from typing import Dict, List
import requests
from ccloud_auth_provider import CCloud_Auth_Provider

class CCloud_Util:
    @staticmethod
    def request_with_paging(url, auth_provider: CCloud_Auth_Provider, params: Dict[str, str]={}, page_size: int=10)->List[str]:
        results = []
        headers_ccloud_api = auth_provider.get_auth_header(url)
        current_url = url
        all_params = params
        all_params["page_size"]= page_size
        while current_url is not None:
            response = requests.get(current_url, 
                                    headers=headers_ccloud_api,
                                    params=all_params)
            current_url = None
            response.raise_for_status()
            if response.status_code != 200:
                error_msg = response.json().get('errors')[0].get('detail')
                raise RuntimeError(f'Unable to list environments (status code: {response.status_code}, message: "{error_msg}")')
            json_data = response.json()
            if json_data is None:
                break;
            if "data" in json_data and json_data["data"] is not None:
                results.extend(json_data["data"])
            metadata = json_data.get('metadata', None)
            if metadata is not None:
                current_url = metadata.get('next', None)
            # Potenially wait for seconds specified by server until sending next request
            rate_limit_reset_secs = int(response.headers.get('Retry-After', '0'))
            time.sleep(rate_limit_reset_secs)
            # Reset to originals params (paging param only required at first call)
            all_params = params

        return results
