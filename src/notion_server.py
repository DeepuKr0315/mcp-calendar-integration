import asyncio
import json
from datetime import datetime
from typing import Any, Sequence
import os
from dotenv import load_dotenv
import requests

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Load environment variables
load_dotenv()

class NotionMCPServer:
    def __init__(self):
        self.server = Server("notion-mcp-server")
        self.notion_api_key = os.getenv('NOTION_API_KEY')
        self.notion_database_id = os.getenv('NOTION_DATABASE_ID')
        self.notion_url = "https://api.notion.com/v1"
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available Notion tools."""
            return [
                types.Tool(
                    name="create_task",
                    description="Create a new task in Notion database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Task title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Task description",
                                "default": ""
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Due date in YYYY-MM-DD format",
                                "default": ""
                            },
                            "priority": {
                                "type": "string",
                                "description": "Task priority (High, Medium, Low)",
                                "enum": ["High", "Medium", "Low"],
                                "default": "Medium"
                            },
                            "source": {
                                "type": "string",
                                "description": "Source of the task (e.g., Calendar, Meeting)",
                                "default": "Calendar"
                            }
                        },
                        "required": ["title"]
                    },
                ),
                types.Tool(
                    name="create_tasks_from_calendar_events",
                    description="Create tasks from calendar events and extract action items",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "events": {
                                "type": "string",
                                "description": "JSON string of calendar events"
                            },
                            "extract_action_items": {
                                "type": "boolean",
                                "description": "Whether to extract action items from event descriptions",
                                "default": True
                            }
                        },
                        "required": ["events"]
                    },
                ),
                types.Tool(
                    name="create_meeting_summary",
                    description="Create a meeting summary with action items in Notion",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "meeting_title": {
                                "type": "string",
                                "description": "Meeting title"
                            },
                            "meeting_date": {
                                "type": "string",
                                "description": "Meeting date in YYYY-MM-DD format"
                            },
                            "attendees": {
                                "type": "string",
                                "description": "Comma-separated list of attendees"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Meeting summary/notes"
                            },
                            "action_items": {
                                "type": "string",
                                "description": "JSON string of action items"
                            }
                        },
                        "required": ["meeting_title", "summary"]
                    },
                ),
                types.Tool(
                    name="get_tasks",
                    description="Get tasks from Notion database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_by": {
                                "type": "string",
                                "description": "Filter tasks by status, priority, or source",
                                "default": ""
                            }
                        },
                        "required": []
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
                if name == "create_task":
                    return await self._create_task(arguments)
                elif name == "create_tasks_from_calendar_events":
                    return await self._create_tasks_from_calendar_events(arguments)
                elif name == "create_meeting_summary":
                    return await self._create_meeting_summary(arguments)
                elif name == "get_tasks":
                    return await self._get_tasks(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )]

    def _get_notion_headers(self):
        """Get headers for Notion API requests."""
        return {
            "Authorization": f"Bearer {self.notion_api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    async def _create_task(self, arguments: dict) -> list[types.TextContent]:
        """Create a single task in Notion."""
        if not self.notion_api_key or not self.notion_database_id:
            return [types.TextContent(
                type="text",
                text="Error: Notion API key or database ID not configured."
            )]

        title = arguments['title']
        description = arguments.get('description', '')
        due_date = arguments.get('due_date', '')
        priority = arguments.get('priority', 'Medium')
        source = arguments.get('source', 'Calendar')

        # Prepare the request payload
        payload = {
            "parent": {"database_id": self.notion_database_id},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": title}}]
                },
                "Status": {
                    "select": {"name": "Not started"}
                },
                "Priority": {
                    "select": {"name": priority}
                },
                "Source": {
                    "select": {"name": source}
                },
                "Created": {
                    "date": {"start": datetime.now().isoformat()}
                }
            }
        }

        # Add due date if provided
        if due_date:
            try:
                datetime.strptime(due_date, '%Y-%m-%d')  # Validate date format
                payload["properties"]["Due Date"] = {
                    "date": {"start": due_date}
                }
            except ValueError:
                pass  # Skip invalid date

        # Add description if provided
        if description:
            payload["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": description}}]
                    }
                }
            ]

        try:
            response = requests.post(
                f"{self.notion_url}/pages",
                headers=self._get_notion_headers(),
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return [types.TextContent(
                    type="text",
                    text=f"✅ Task created successfully: '{title}'\nPage ID: {result['id']}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Error creating task: {response.status_code} - {response.text}"
                )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ Error creating task: {str(e)}"
            )]

    async def _create_tasks_from_calendar_events(self, arguments: dict) -> list[types.TextContent]:
        """Create tasks from calendar events with action item extraction."""
        events_json = arguments['events']
        extract_action_items = arguments.get('extract_action_items', True)

        try:
            events = json.loads(events_json)
            created_tasks = []
            
            for event in events:
                title = event.get('title', 'Untitled Event')
                description = event.get('description', '')
                start_time = event.get('start_time', '')
                location = event.get('location', '')
                
                # Extract date from start_time for due date
                due_date = ""
                if start_time:
                    try:
                        if 'T' in start_time:
                            due_date = start_time.split('T')[0]
                        else:
                            due_date = start_time
                    except:
                        pass

                # Create main event task
                event_description = f"📅 Calendar Event\n"
                if location != 'No location specified':
                    event_description += f"📍 Location: {location}\n"
                if description != 'No description':
                    event_description += f"📝 Notes: {description}\n"
                
                main_task_args = {
                    'title': f"📅 {title}",
                    'description': event_description,
                    'due_date': due_date,
                    'priority': 'Medium',
                    'source': 'Calendar'
                }
                
                result = await self._create_task(main_task_args)
                created_tasks.append(f"Event: {title}")

                # Extract action items if requested
                if extract_action_items and description != 'No description':
                    action_items = self._extract_action_items_from_text(description)
                    
                    for item in action_items:
                        action_task_args = {
                            'title': f"🎯 {item}",
                            'description': f"Action item from meeting: {title}",
                            'due_date': due_date,
                            'priority': 'High',
                            'source': 'Meeting'
                        }
                        
                        await self._create_task(action_task_args)
                        created_tasks.append(f"Action: {item}")

            return [types.TextContent(
                type="text",
                text=f"✅ Created {len(created_tasks)} tasks from calendar events:\n" + 
                     "\n".join([f"• {task}" for task in created_tasks])
            )]

        except json.JSONDecodeError:
            return [types.TextContent(
                type="text",
                text="❌ Error: Invalid JSON format for events."
            )]
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ Error creating tasks from events: {str(e)}"
            )]

    def _extract_action_items_from_text(self, text: str) -> list[str]:
        """Extract action items from text."""
        action_keywords = ['todo', 'action item', 'follow up', 'assign', 'task', 'deadline', 'due']
        lines = text.lower().split('\n')
        action_items = []
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and any(keyword in line for keyword in action_keywords):
                # Clean up the action item
                clean_item = line_stripped.replace('- ', '').replace('* ', '').strip()
                if clean_item and len(clean_item) > 10:  # Avoid very short items
                    action_items.append(clean_item[:100])  # Limit length
        
        return action_items[:5]  # Limit to 5 action items

    async def _create_meeting_summary(self, arguments: dict) -> list[types.TextContent]:
        """Create a meeting summary with action items."""
        meeting_title = arguments['meeting_title']
        meeting_date = arguments.get('meeting_date', datetime.now().strftime('%Y-%m-%d'))
        attendees = arguments.get('attendees', '')
        summary = arguments['summary']
        action_items_json = arguments.get('action_items', '[]')

        try:
            action_items = json.loads(action_items_json) if action_items_json else []
            
            # Create meeting summary task
            meeting_description = f"📊 Meeting Summary\n"
            if attendees:
                meeting_description += f"👥 Attendees: {attendees}\n"
            meeting_description += f"📝 Summary:\n{summary}\n"
            
            if action_items:
                meeting_description += f"\n🎯 Action Items:\n"
                for item in action_items[:5]:  # Limit to 5 items
                    meeting_description += f"• {item}\n"

            summary_task_args = {
                'title': f"📊 Meeting Summary: {meeting_title}",
                'description': meeting_description,
                'due_date': meeting_date,
                'priority': 'Medium',
                'source': 'Meeting'
            }
            
            await self._create_task(summary_task_args)
            
            # Create individual action item tasks
            created_actions = 0
            for item in action_items[:5]:  # Limit to 5 action items
                action_task_args = {
                    'title': f"🎯 {item}",
                    'description': f"Action item from meeting: {meeting_title}",
                    'due_date': meeting_date,
                    'priority': 'High',
                    'source': 'Meeting'
                }
                
                await self._create_task(action_task_args)
                created_actions += 1

            return [types.TextContent(
                type="text",
                text=f"✅ Created meeting summary and {created_actions} action items for: {meeting_title}"
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ Error creating meeting summary: {str(e)}"
            )]

    async def _get_tasks(self, arguments: dict) -> list[types.TextContent]:
        """Get tasks from Notion database."""
        filter_by = arguments.get('filter_by', '')

        try:
            url = f"{self.notion_url}/databases/{self.notion_database_id}/query"
            
            payload = {
                "page_size": 10
            }
            
            # Add filter if specified
            if filter_by:
                if filter_by.lower() in ['high', 'medium', 'low']:
                    payload["filter"] = {
                        "property": "Priority",
                        "select": {"equals": filter_by.title()}
                    }

            response = requests.post(
                url,
                headers=self._get_notion_headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                tasks = []
                
                for page in data.get('results', []):
                    properties = page.get('properties', {})
                    
                    title = "Untitled"
                    if 'Name' in properties and properties['Name'].get('title'):
                        title = properties['Name']['title'][0]['text']['content']
                    
                    status = "Unknown"
                    if 'Status' in properties and properties['Status'].get('select'):
                        status = properties['Status']['select']['name']
                    
                    priority = "Unknown"
                    if 'Priority' in properties and properties['Priority'].get('select'):
                        priority = properties['Priority']['select']['name']
                    
                    tasks.append(f"• {title} [{status}] - {priority} priority")

                if tasks:
                    return [types.TextContent(
                        type="text",
                        text=f"📋 Found {len(tasks)} tasks:\n" + "\n".join(tasks)
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="📋 No tasks found in the database."
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Error fetching tasks: {response.status_code} - {response.text}"
                )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ Error fetching tasks: {str(e)}"
            )]

    async def run(self):
        """Run the MCP server."""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="notion-mcp-server",
                    server_version="0.1.0",
                    capabilities=types.ServerCapabilities(
                        tools=types.ToolsCapability()
                    ),
                ),
            )

async def main():
    """Main function to run the Notion MCP server."""
    server = NotionMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())