import asyncio
import json
import sys
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class CalendarToNotionWorkflow:
    def __init__(self):
        self.calendar_server = "src/calendar_server.py"
        self.notion_server = "src/notion_server.py"
    
    async def run_daily_sync(self):
        """Run the daily calendar to Notion sync workflow."""
        print("🚀 Starting Calendar to Notion Integration...")
        print("=" * 60)
        
        # Step 1: Get today's calendar events
        calendar_events = await self._get_calendar_events()
        
        if not calendar_events:
            print("📅 No calendar events found for today.")
            return
        
        # Step 2: Process events and create tasks in Notion
        await self._process_events_to_notion(calendar_events)
        
        print("\n" + "=" * 60)
        print("✅ Daily sync completed successfully!")
    
    async def _get_calendar_events(self):
        """Fetch today's calendar events."""
        print("📅 Fetching today's calendar events...")
        
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.calendar_server],
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Get today's events
                    result = await session.call_tool("get_todays_events", {})
                    
                    for content in result.content:
                        if content.type == "text":
                            try:
                                events = json.loads(content.text)
                                print(f"📊 Found {len(events)} calendar events")
                                return events
                            except json.JSONDecodeError:
                                if "No events found" in content.text:
                                    print("📅 No events scheduled for today")
                                    return []
                                else:
                                    print(f"❌ Error parsing calendar data: {content.text}")
                                    return []
            
        except Exception as e:
            print(f"❌ Error fetching calendar events: {e}")
            return []
    
    async def _process_events_to_notion(self, events):
        """Process calendar events and create tasks in Notion."""
        print(f"\n📝 Processing {len(events)} events for Notion...")
        
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.notion_server],
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Convert events to tasks
                    events_json = json.dumps(events)
                    result = await session.call_tool(
                        "create_tasks_from_calendar_events", 
                        {
                            "events": events_json,
                            "extract_action_items": True
                        }
                    )
                    
                    for content in result.content:
                        if content.type == "text":
                            print(f"📋 Notion Result: {content.text}")
                    
                    # Also create meeting summaries for events with descriptions
                    await self._create_meeting_summaries(session, events)
                    
        except Exception as e:
            print(f"❌ Error processing events to Notion: {e}")
    
    async def _create_meeting_summaries(self, session, events):
        """Create detailed meeting summaries for events with substantial content."""
        print("\n📊 Creating meeting summaries...")
        
        for event in events:
            title = event.get('title', '')
            description = event.get('description', '')
            attendees = event.get('attendees', [])
            start_time = event.get('start_time', '')
            
            # Only create summaries for events that look like meetings
            if (description != 'No description' and 
                len(description) > 50 and 
                any(keyword in description.lower() for keyword in 
                    ['meeting', 'discuss', 'review', 'action', 'todo', 'follow'])):
                
                # Extract date from start_time
                meeting_date = datetime.now().strftime('%Y-%m-%d')
                if start_time:
                    try:
                        if 'T' in start_time:
                            meeting_date = start_time.split('T')[0]
                        else:
                            meeting_date = start_time
                    except:
                        pass
                
                # Extract action items from description
                action_items = self._extract_action_items_simple(description)
                
                try:
                    result = await session.call_tool(
                        "create_meeting_summary",
                        {
                            "meeting_title": title,
                            "meeting_date": meeting_date,
                            "attendees": ", ".join(attendees) if attendees else "",
                            "summary": description,
                            "action_items": json.dumps(action_items)
                        }
                    )
                    
                    for content in result.content:
                        if content.type == "text":
                            print(f"📊 Meeting Summary: {content.text}")
                            
                except Exception as e:
                    print(f"❌ Error creating meeting summary for '{title}': {e}")
    
    def _extract_action_items_simple(self, text):
        """Simple action item extraction."""
        action_keywords = ['todo', 'action item', 'follow up', 'assign', 'task', 'deadline', 'due']
        lines = text.lower().split('\n')
        action_items = []
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and any(keyword in line for keyword in action_keywords):
                clean_item = line_stripped.replace('- ', '').replace('* ', '').strip()
                if clean_item and len(clean_item) > 10:
                    action_items.append(clean_item[:80])  # Limit length
        
        return action_items[:3]  # Limit to 3 action items
    
    async def run_custom_date_sync(self, date_str):
        """Run sync for a specific date (YYYY-MM-DD format)."""
        print(f"🚀 Starting Calendar to Notion sync for {date_str}...")
        print("=" * 60)
        
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.calendar_server],
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Get events for specific date
                    result = await session.call_tool("get_events_by_date", {"date": date_str})
                    
                    events = []
                    for content in result.content:
                        if content.type == "text":
                            try:
                                events = json.loads(content.text)
                                print(f"📊 Found {len(events)} events for {date_str}")
                                break
                            except json.JSONDecodeError:
                                if "No events found" in content.text:
                                    print(f"📅 No events found for {date_str}")
                                    return
                    
                    if events:
                        await self._process_events_to_notion(events)
                    
        except Exception as e:
            print(f"❌ Error in custom date sync: {e}")

async def main():
    """Main function with menu options."""
    workflow = CalendarToNotionWorkflow()
    
    print("📅➡️📝 Calendar to Notion Integration Tool")
    print("=" * 50)
    print("1. Sync today's calendar events to Notion")
    print("2. Sync specific date to Notion")
    print("3. Test connection to both servers")
    print("=" * 50)
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        await workflow.run_daily_sync()
    
    elif choice == "2":
        date_input = input("Enter date (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(date_input, '%Y-%m-%d')  # Validate date format
            await workflow.run_custom_date_sync(date_input)
        except ValueError:
            print("❌ Invalid date format. Please use YYYY-MM-DD.")
    
    elif choice == "3":
        print("🔧 Testing server connections...")
        
        # Test calendar server
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[workflow.calendar_server],
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    print(f"✅ Calendar server: {len(tools.tools)} tools available")
        except Exception as e:
            print(f"❌ Calendar server error: {e}")
        
        # Test Notion server
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[workflow.notion_server],
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    print(f"✅ Notion server: {len(tools.tools)} tools available")
        except Exception as e:
            print(f"❌ Notion server error: {e}")
    
    else:
        print("❌ Invalid choice. Please run again.")

if __name__ == "__main__":
    asyncio.run(main())