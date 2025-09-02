import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Sequence
import os
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class CalendarMCPServer:
    def __init__(self):
        self.server = Server("calendar-mcp-server")
        self.service = None
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available calendar tools."""
            return [
                types.Tool(
                    name="get_todays_events",
                    description="Get all events for today from Google Calendar",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: 'primary')",
                                "default": "primary"
                            }
                        },
                        "required": []
                    },
                ),
                types.Tool(
                    name="get_events_by_date",
                    description="Get events for a specific date",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format"
                            },
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: 'primary')",
                                "default": "primary"
                            }
                        },
                        "required": ["date"]
                    },
                ),
                types.Tool(
                    name="extract_meeting_details",
                    description="Extract and summarize details from a meeting/event",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "event_text": {
                                "type": "string",
                                "description": "Event description or meeting notes"
                            }
                        },
                        "required": ["event_text"]
                    },
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict[str, Any] | None
        ) -> list[types.TextContent]:
            """Handle tool calls."""
            if arguments is None:
                arguments = {}

            try:
                if name == "get_todays_events":
                    return await self._get_todays_events(arguments)
                elif name == "get_events_by_date":
                    return await self._get_events_by_date(arguments)
                elif name == "extract_meeting_details":
                    return await self._extract_meeting_details(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )]

    async def _authenticate_google_calendar(self):
        """Authenticate with Google Calendar API."""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # If there are no valid credentials, get them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError(
                        "credentials.json file not found. Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)

    async def _get_todays_events(self, arguments: dict) -> list[types.TextContent]:
        """Get today's events from Google Calendar."""
        if not self.service:
            await self._authenticate_google_calendar()
        
        calendar_id = arguments.get('calendar_id', 'primary')
        
        # Get today's date range
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        today_iso = today.isoformat() + 'Z'
        tomorrow_iso = tomorrow.isoformat() + 'Z'
        
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=today_iso,
                timeMax=tomorrow_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return [types.TextContent(
                    type="text",
                    text="No events found for today."
                )]
            
            # Format events
            event_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'No title')
                description = event.get('description', 'No description')
                location = event.get('location', 'No location specified')
                
                event_info = {
                    'title': summary,
                    'start_time': start,
                    'description': description,
                    'location': location,
                    'attendees': [attendee.get('email') for attendee in event.get('attendees', [])]
                }
                event_list.append(event_info)
            
            return [types.TextContent(
                type="text",
                text=json.dumps(event_list, indent=2)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching events: {str(e)}"
            )]

    async def _get_events_by_date(self, arguments: dict) -> list[types.TextContent]:
        """Get events for a specific date."""
        if not self.service:
            await self._authenticate_google_calendar()
        
        date_str = arguments['date']
        calendar_id = arguments.get('calendar_id', 'primary')
        
        try:
            # Parse the date and create time range
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            start_iso = start_of_day.isoformat() + 'Z'
            end_iso = end_of_day.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return [types.TextContent(
                    type="text",
                    text=f"No events found for {date_str}."
                )]
            
            # Format events
            event_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'No title')
                description = event.get('description', 'No description')
                location = event.get('location', 'No location specified')
                
                event_info = {
                    'title': summary,
                    'start_time': start,
                    'description': description,
                    'location': location,
                    'attendees': [attendee.get('email') for attendee in event.get('attendees', [])]
                }
                event_list.append(event_info)
            
            return [types.TextContent(
                type="text",
                text=json.dumps(event_list, indent=2)
            )]
            
        except ValueError:
            return [types.TextContent(
                type="text",
                text="Invalid date format. Please use YYYY-MM-DD."
            )]
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error fetching events: {str(e)}"
            )]

    async def _extract_meeting_details(self, arguments: dict) -> list[types.TextContent]:
        """Extract key details and action items from meeting text."""
        event_text = arguments['event_text']
        
        # Simple text analysis - you could integrate with OpenAI or other AI services here
        analysis = {
            'summary': 'Meeting details extracted',
            'potential_action_items': [],
            'key_topics': [],
            'attendees_mentioned': []
        }
        
        # Simple keyword extraction for action items
        action_keywords = ['todo', 'action item', 'follow up', 'assign', 'task', 'deadline', 'due']
        lines = event_text.lower().split('\n')
        
        for line in lines:
            if any(keyword in line for keyword in action_keywords):
                analysis['potential_action_items'].append(line.strip())
        
        # Extract potential topics (sentences with key business words)
        topic_keywords = ['discuss', 'review', 'plan', 'strategy', 'budget', 'timeline', 'project']
        for line in lines:
            if any(keyword in line.lower() for keyword in topic_keywords):
                analysis['key_topics'].append(line.strip())
        
        return [types.TextContent(
            type="text",
            text=json.dumps(analysis, indent=2)
        )]

    async def run(self):
        """Run the MCP server."""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="calendar-mcp-server",
                    server_version="0.1.0",
                    capabilities=types.ServerCapabilities(
                        tools=types.ToolsCapability()
                    ),
                ),
            )

async def main():
    """Main function to run the calendar MCP server."""
    server = CalendarMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())