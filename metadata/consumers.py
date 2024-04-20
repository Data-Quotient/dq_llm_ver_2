# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .managers.session_manager import UserSession
from taskweaver.app.app import TaskWeaverApp

# This would be a global variable, potentially in the same module as your consumer
user_sessions = {}

app_dir = "metadata/project"
app = TaskWeaverApp(app_dir=app_dir)  # Initialize your AI app

class ChatAIConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept the WebSocket connection without authentication for now
        await self.accept()

    async def disconnect(self, close_code):
        # Handle cleanup on disconnect
        session = user_sessions.pop(self.session_id, None)
        if session:
            # You can also handle additional cleanup, if necessary
            pass

    async def receive(self, text_data):
        # Process incoming messages from the user
        text_data_json = json.loads(text_data)
        # Check for the expected message type
        if text_data_json.get('type') == 'authenticate':
            # Handle authentication
            auth_token = text_data_json.get('token')
            session_id = text_data_json.get('session_id')
            datasource_id = text_data_json.get('datasource_id')
            if not await self.authenticate_token(auth_token):
                # Close the connection if the token is invalid
                await self.close(code=4001)
                return
            # Authentication successful, create the AI client session and store the user session
            self.session_id = session_id  # Store session_id on the instance for disconnect cleanup
            ai_client = app.get_session()  # Create a session for the AI client
            user_sessions[session_id] = UserSession(session_id, auth_token, datasource_id, ai_client)
            await self.send(text_data=json.dumps({"message": "Authenticated successfully"}))
        else:
            # Handle other message types, such as AI chat messages
            message = text_data_json.get("message")
            session = user_sessions.get(self.session_id)
            if session and session.ai_client:
                # Use the session's AI client to handle the message and get a response
                ai_response = await self.handle_ai_response(message, session.ai_client)
                await self.send(text_data=json.dumps({"message": ai_response}))
            else:
                # Session not found or message received before authentication
                await self.send(text_data=json.dumps({"error": "Unauthorized"}))

    async def handle_ai_response(self, message, ai_client):
        # Using the ai_client to send the message to the AI and receive a response
        response_round = ai_client.send_message(message)
        # Convert the AI's response to a dictionary format and send it back
        response_dict = response_round.to_dict()
        return response_dict


    async def authenticate_token(self, token):
        # Implement actual token authentication logic here
        # For now, assuming all tokens are valid
        return True