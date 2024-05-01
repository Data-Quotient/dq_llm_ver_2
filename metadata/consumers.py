# chat/consumers.py
import json
import asyncio
import logging

from typing import Dict
from concurrent.futures import ThreadPoolExecutor
from channels.generic.websocket import AsyncWebsocketConsumer

from .managers.session_manager import UserSession

from taskweaver.app.app import TaskWeaverApp
from .event_handler import CustomSessionEventHandler


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This would be a global variable, potentially in the same module as your consumer
user_sessions = {}

app_dir = "metadata/project"
app = TaskWeaverApp(app_dir=app_dir)  # Initialize your AI app


executor = ThreadPoolExecutor()

class ChatAIConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract session_id and datasource_id from the URL path
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.datasource_id = self.scope['url_route']['kwargs']['datasource_id']

        logger.info(f"Attempting to connect: session_id={self.session_id}, datasource_id={self.datasource_id}")
        # Accept the WebSocket connection
        await self.accept()



        # Create a new AI session and store it in the user_sessions dictionary
        self.event_handler = CustomSessionEventHandler(self)
        asyncio.create_task(self.process_message_queue())

        # Asynchronously create an AI session to avoid blocking the WebSocket connection
        ai_client = await asyncio.get_event_loop().run_in_executor(executor, app.get_session)
        
        user_sessions[self.session_id] = UserSession(
            session_id=self.session_id, 
            auth_token=None,  # Token will be set after authentication
            datasource_id=self.datasource_id, 
            ai_client=ai_client
        )
        
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
                await self.handle_ai_response(message, session.ai_client)
                logger.info(f"Message processed and response sent for session_id={self.session_id}")
            else:
                # Session not found or message received before authentication
                await self.send(text_data=json.dumps({"error": "Unauthorized"}))
                logger.warning(f"Unauthorized access attempt or session not found for session_id={self.session_id}")

    async def handle_ai_response(self, message, ai_client):
        await asyncio.get_event_loop().run_in_executor(
            executor, ai_client.send_message, message, self.event_handler
        )
        logger.info(f"Message processed and response sent for session_id={self.session_id}")

    async def process_message_queue(self):
        while True:
            event = await self.event_handler.message_queue.get()
            # Serialize and send the event as JSON
            await self.send(text_data=json.dumps(event))
            self.event_handler.message_queue.task_done()
        

    async def authenticate_token(self, token):
        logger.info(f"Authenticating token: {token}")
        # Implement actual token authentication logic here
        # For now, assuming all tokens are valid
        return True
    

