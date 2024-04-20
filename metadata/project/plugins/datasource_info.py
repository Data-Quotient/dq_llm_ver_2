import requests
from taskweaver.plugin import Plugin, register_plugin

from dotenv import load_dotenv
import os 
# Load environment variables from the .env file
load_dotenv()

# Retrieve environment variables
API_HOST = os.getenv("API_HOST", "192.168.1.47")
API_PORT = os.getenv("API_PORT", "8000")


@register_plugin
class DatasourceInfoPlugin(Plugin):
    def __call__(self, datasource_id: int, auth_token: str):
        """
        Fetches information of a particular datasource using its datasource ID.

        :param datasource_id: The ID of the datasource to fetch information for.
        :param auth_token: The authentication token to include in the request headers.
        :return: A tuple containing the datasource information dictionary and a description string.
        """
        # Build the full URL using environment variables
        url = f"http://{API_HOST}:{API_PORT}/api/datasources/{datasource_id}/"
        
        headers = {
            "Authorization": f"Token {auth_token}"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success":
                datasource_info = data["data"]
                description = f"Datasource information fetched successfully for datasource ID {datasource_id}."
            else:
                datasource_info = None
                description = f"Failed to fetch datasource information for datasource ID {datasource_id}. Message: {data['message']}"
        except requests.exceptions.RequestException as e:
            datasource_info = None
            description = f"An error occurred while fetching datasource information for datasource ID {datasource_id}. Error: {str(e)}"

        return datasource_info, description