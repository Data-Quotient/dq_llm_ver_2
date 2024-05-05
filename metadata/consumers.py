# chat/consumers.py
import json
import asyncio
import logging
import requests
import os
import re

from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from channels.generic.websocket import AsyncWebsocketConsumer

from .managers.session_manager import UserSession

from taskweaver.app.app import TaskWeaverApp
from taskweaver.memory.attachment import AttachmentType

from .event_handler import CustomSessionEventHandler


from typing import List, Tuple
from dataclasses import dataclass

from typing import List, Tuple
from dataclasses import dataclass

import os
from django.conf import settings
from shutil import copyfile

def create_user_folder(session_id, file_path):
    # Define the folder path based on user_id and session_id
    folder_path = os.path.join(settings.MEDIA_ROOT, str(session_id))
    
    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Extract file name from the file path
    file_name = os.path.basename(file_path)

    # Check if the file already exists in the destination folder
    destination_file_path = os.path.join(folder_path, file_name)
    if os.path.exists(destination_file_path):
        raise FileExistsError("File already exists in the destination folder.")

    # Copy the file to the destination folder
    copyfile(file_path, destination_file_path)

    # Return the full file path relative to the MEDIA_URL
    return os.path.join(settings.MEDIA_URL, str(session_id), file_name)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This would be a global variable, potentially in the same module as your consumer
user_sessions = {}

app_dir = "metadata/project"
app = TaskWeaverApp(app_dir=app_dir)  # Initialize your AI app


executor = ThreadPoolExecutor()



def is_link_clickable(url: str):
    if url:
        try:
            response = requests.get(url)
            # If the response status code is 200, the link is clickable
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    else:
        return False

def file_display(files: List[Tuple[str, str]], session_cwd_path: str, session_id):
    elements = []
    for file_name, file_path in files:
        # Check if the path is absolute or needs to be combined with the current working directory
        full_path = os.path.join(session_cwd_path, file_path) if not os.path.isabs(file_path) else file_path

        new_file_path = create_user_folder(session_id, full_path)
        # Determine the file extension and create appropriate elements
        if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            # Image files
            element = {
                "type": "image",
                "path": new_file_path,
                "name": file_name,
                "display": "inline"  # This will be used to render the image directly in the chat
            }
        elif file_path.lower().endswith(".csv"):
            # CSV files - assume we want to show a preview or provide a download
            element = {
                "type": "file",
                "path": new_file_path,
                "name": file_name,
                "display": "link",  # Link to download or view
                "preview": True    # Optional: Implement logic to show a preview of the CSV
            }
        elif file_path.lower().endswith((".mp3", ".wav")):
            # Audio files
            element = {
                "type": "audio",
                "path": new_file_path,
                "name": file_name,
                "display": "stream"  # Audio can be streamed directly in the chat
            }
        else:
            # Default handler for other file types
            element = {
                "type": "file",
                "path": new_file_path,
                "name": file_name,
                "display": "link"  # Generic file handler, links to download
            }
        elements.append(element)
    return elements



class ChatAIConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract session_id and datasource_id from the URL path
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.datasource_id = self.scope['url_route']['kwargs']['datasource_id']

        logger.info(f"Attempting to connect: session_id={self.session_id}, datasource_id={self.datasource_id}")
        # Accept the WebSocket connection
        await self.accept()

        # Asynchronously create an AI session to avoid blocking the WebSocket connection
        ai_client = await asyncio.get_event_loop().run_in_executor(executor, app.get_session)
        
        user_sessions[self.session_id] = UserSession(
            session_id=self.session_id, 
            auth_token=None,  # Token will be set after authentication
            datasource_id=self.datasource_id, 
            ai_client=ai_client
        )

        self.user_session = user_sessions[self.session_id]

        # Create a new AI session and store it in the user_sessions dictionary
        self.event_handler = CustomSessionEventHandler(self.user_session)
        asyncio.create_task(self.process_message_queue())
        
        user_sessions[self.session_id].ai_client.update_session_var(variables = {"datasource_id": self.datasource_id})

        logger.info(f"WebSocket connection accepted and AI session created for session_id={self.session_id}")


    async def disconnect(self, close_code):
        # Handle cleanup on disconnect
        session = user_sessions.pop(self.session_id, None)
        if session:
            session.ai_client.stop()  # Ensure session cleanup
            logger.info(f"Session {self.session_id} disconnected and cleaned up")
        
    async def receive(self, text_data):

        # Process incoming messages from the user
        text_data_json = json.loads(text_data)

        logger.info(f"Received message: {text_data_json}")

        # Check for the expected message type
        if text_data_json.get('type') == 'authenticate':
            # Handle authentication
            auth_token = text_data_json.get('token')
            session_id = self.scope['url_route']['kwargs']['session_id']
            datasource_id = self.scope['url_route']['kwargs']['datasource_id']
            if not await self.authenticate_token(auth_token):
                # Close the connection if the token is invalid
                logger.error(f"Authentication failed for token={auth_token}")
                await self.close(code=4001)
                return
            
            # Update the auth token in the user session
            user_sessions[session_id].auth_token = auth_token
            

            
            user_sessions[session_id].ai_client.update_session_var(variables = {"auth_token": auth_token})


            logger.info(f"User authenticated successfully for session_id={session_id} and ds id {datasource_id}")

            await self.send(text_data=json.dumps({"message": "Authenticated successfully"}))
        else:

            
            # Handle other message types, such as AI chat messages
            message = text_data_json.get("message")
            session = user_sessions.get(self.session_id)
            if session and session.ai_client:
                # Use the session's AI client to handle the message and get a response
                response_round = await self.handle_ai_response(message, session.ai_client)

                final_response = self.handle_response_round(session.ai_client, response_round)
                await self.send(text_data=json.dumps(final_response))

                logger.info(f"Message processed and response sent for session_id={self.session_id}")
            else:
                # Session not found or message received before authentication
                await self.send(text_data=json.dumps({"error": "Unauthorized"}))
                logger.warning(f"Unauthorized access attempt or session not found for session_id={self.session_id}")

    def handle_response_round(self, session, response_round):

        session_cwd_path = session.execution_cwd

        artifact_paths = [
            p
            for p in response_round.post_list
            for a in p.attachment_list
            if a.type == AttachmentType.artifact_paths
            for p in a.content
        ]

        for post in [p for p in response_round.post_list if p.send_to == "User"]:
            files: List[Tuple[str, str]] = []
            if len(artifact_paths) > 0:
                for file_path in artifact_paths:
                    # if path is image or csv (the top 5 rows), display it
                    file_name = os.path.basename(file_path)
                    files.append((file_name, file_path))

            # Extract the file path from the message and display it
            user_msg_content = post.message
            pattern = r"(!?)\[(.*?)\]\((.*?)\)"
            matches = re.findall(pattern, user_msg_content)
            for match in matches:
                img_prefix, file_name, file_path = match
                if "://" in file_path:
                    if not is_link_clickable(file_path):
                        user_msg_content = user_msg_content.replace(
                            f"{img_prefix}[{file_name}]({file_path})",
                            file_name,
                        )
                    continue
                files.append((file_name, file_path))
                user_msg_content = user_msg_content.replace(
                    f"{img_prefix}[{file_name}]({file_path})",
                    file_name,
                )
            elements = file_display(files, session_cwd_path, self.session_id)

            elements=elements if len(elements) > 0 else None

            final_response = {
                "author": "DQ Data Assistant",
                "content":f"{user_msg_content}",
                "elements": elements,
            }
            return final_response

    async def handle_ai_response(self, message, ai_client):
        response_round = await asyncio.get_event_loop().run_in_executor(
            executor, ai_client.send_message, message, self.event_handler
        )
        logger.info(f"Message processed and response sent for session_id={self.session_id}")
        return response_round

    async def process_message_queue(self):
        while True:
            event = await self.user_session.message_queue.get()
            # Serialize and send the event as JSON
            await self.send(text_data=json.dumps(event))
            self.user_session.message_queue.task_done()
        

    async def authenticate_token(self, token):
        logger.info(f"Authenticating token: {token}")
        # Implement actual token authentication logic here
        # For now, assuming all tokens are valid
        return True
    

