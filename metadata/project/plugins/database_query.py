import requests
from taskweaver.plugin import Plugin, register_plugin

from dotenv import load_dotenv
import os 
load_dotenv()

# Retrieve environment variables
API_HOST = os.getenv("API_HOST", "192.168.1.47")
API_PORT = os.getenv("API_PORT", "8000")

@register_plugin
class DatabaseQueryPlugin(Plugin):
    def __call__(self, query: str):
        """
        Executes a query on a specific datasource using its datasource ID.

        :param datasource_id: The ID of the datasource to run the query on.
        :param query: The SQL query to execute.
        :return: A tuple containing the query results and a description string.
        """

        datasource_id = self.ctx.get_session_var("datasource_id")
        if datasource_id is None:
            raise ValueError("No datasource ID found in session.")
        
        url = f"http://{API_HOST}:{API_PORT}/api/datasources/query/"
        
        data = {
            "data_source_id": datasource_id,
            "query": query
        }

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            result = response.json()

            if result["status"] == "success":
                query_results = result["data"]
                description = f"Query executed successfully on datasource ID {datasource_id}."
            else:
                query_results = None
                description = f"Failed to execute query on datasource ID {datasource_id}. Message: {result['message']}"
        except requests.exceptions.RequestException as e:
            query_results = None
            description = f"An error occurred while executing the query on datasource ID {datasource_id}. Error: {str(e)}"

        return query_results, description