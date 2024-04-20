import requests
from taskweaver.plugin import Plugin, register_plugin

from dotenv import load_dotenv
import os 
load_dotenv()


# Retrieve environment variables
API_HOST = os.getenv("API_HOST", "192.168.1.47")
API_PORT = os.getenv("API_PORT", "8000")

@register_plugin
class MetadataFetchPlugin(Plugin):
    def __call__(self, datasource_id: int):
        """
        Fetches metadata of a particular datasource using its datasource ID.

        :param datasource_id: The ID of the datasource to fetch metadata for.
        :return: A tuple containing the metadata dictionary and a description string.
        """
        # Build the full URL using environment variables
        url = f"http://{API_HOST}:{API_PORT}/api/metadata/fetch/{datasource_id}/"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success":
                metadata = data["data"]
                description = f"Metadata fetched successfully for datasource ID {datasource_id}."
            else:
                metadata = None
                description = f"Failed to fetch metadata for datasource ID {datasource_id}. Message: {data['message']}"

        except requests.exceptions.RequestException as e:
            metadata = None
            description = f"An error occurred while fetching metadata for datasource ID {datasource_id}. Error: {str(e)}"

        return metadata, description
    

if __name__ == "__main__":
    from taskweaver.plugin.context import temp_context

    with temp_context() as temp_ctx:
        render = MetadataFetchPlugin(name="datasource_info", ctx=temp_ctx, config={})
        print(render(datasource_id = 34))