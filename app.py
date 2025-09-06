import streamlit as st
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import time

# Page configuration
st.set_page_config(
    page_title="Calendar-Notion MCP Integration",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 1rem;
        color: white;
    }
    
    .metric-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .success-message {
        background: rgba(76, 175, 80, 0.1);
        border-left: 5px solid #4CAF50;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .error-message {
        background: rgba(244, 67, 54, 0.1);
        border-left: 5px solid #f44336;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .info-message {
        background: rgba(33, 150, 243, 0.1);
        border-left: 5px solid #2196F3;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .event-card {
        background: linear-gradient(135deg, #4FC3F7 0%, #29B6F6 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
    }
    
    .task-card {
        background: linear-gradient(135deg, #81C784 0%, #66BB6A 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
    }
    
    .action-card {
        background: linear-gradient(135deg, #FFB74D 0%, #FFA726 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitMCPDashboard:
    def __init__(self):
        self.calendar_server = "src/calendar_server.py"
        self.notion_server = "src/notion_server.py"
        
        # Initialize session state
        if 'events' not in st.session_state:
            st.session_state.events = []
        if 'tasks' not in st.session_state:
            st.session_state.tasks = []
        if 'sync_history' not in st.session_state:
            st.session_state.sync_history = []
        if 'stats' not in st.session_state:
            st.session_state.stats = {
                'events_today': 0,
                'tasks_created': 0,
                'action_items': 0,
                'time_saved': 0
            }
    
    async def get_calendar_events(self, date_str=None):
        """Fetch calendar events from MCP server."""
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.calendar_server],
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    if date_str:
                        result = await session.call_tool("get_events_by_date", {"date": date_str})
                    else:
                        result = await session.call_tool("get_todays_events", {})
                    
                    for content in result.content:
                        if content.type == "text":
                            try:
                                events = json.loads(content.text)
                                return events if isinstance(events, list) else []
                            except json.JSONDecodeError:
                                if "No events found" in content.text:
                                    return []
                                else:
                                    st.error(f"Error parsing calendar data: {content.text}")
                                    return []
        except Exception as e:
            st.error(f"Error fetching calendar events: {e}")
            return []
    
    async def create_notion_tasks(self, events):
        """Create tasks in Notion from calendar events."""
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.notion_server],
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
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
                            return content.text
                    
        except Exception as e:
            return f"Error creating tasks: {e}"
    
    async def test_servers(self):
        """Test both MCP servers."""
        results = {"calendar": False, "notion": False, "calendar_tools": 0, "notion_tools": 0}
        
        # Test calendar server
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.calendar_server],
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    results["calendar"] = True
                    results["calendar_tools"] = len(tools.tools)
        except Exception as e:
            st.error(f"Calendar server error: {e}")
        
        # Test notion server
        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.notion_server],
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    results["notion"] = True
                    results["notion_tools"] = len(tools.tools)
        except Exception as e:
            st.error(f"Notion server error: {e}")
        
        return results

def run_async(coro):
    """Helper function to run async code in Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

def main():
    dashboard = StreamlitMCPDashboard()
    
    # Header
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1 style='color: #667eea; font-size: 3rem; margin-bottom: 1rem;'>
            📅 Calendar-Notion MCP Integration
        </h1>
        <p style='font-size: 1.2rem; color: #666;'>
            Automatically sync your Google Calendar events to Notion tasks with AI-powered action item extraction
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Control Panel")
        
        # Server Status
        st.subheader("Server Status")
        if st.button("🔍 Test Connections", use_container_width=True):
            with st.spinner("Testing server connections..."):
                results = run_async(dashboard.test_servers())
                
                if results["calendar"]:
                    st.success(f"✅ Calendar Server: {results['calendar_tools']} tools")
                else:
                    st.error("❌ Calendar Server: Offline")
                
                if results["notion"]:
                    st.success(f"✅ Notion Server: {results['notion_tools']} tools")
                else:
                    st.error("❌ Notion Server: Offline")
        
        st.divider()
        
        # Sync Controls
        st.subheader("📅 Sync Controls")
        
        # Today's events
        if st.button("🔄 Sync Today's Events", use_container_width=True, type="primary"):
            with st.spinner("Fetching today's calendar events..."):
                events = run_async(dashboard.get_calendar_events())
                st.session_state.events = events
                st.session_state.stats['events_today'] = len(events)
                
                if events:
                    st.success(f"✅ Found {len(events)} events for today!")
                    
                    # Create tasks in Notion
                    with st.spinner("Creating tasks in Notion..."):
                        result = run_async(dashboard.create_notion_tasks(events))
                        
                        # Parse result to count created tasks
                        if "Created" in result and "tasks" in result:
                            try:
                                # Extract number of tasks created
                                import re
                                matches = re.findall(r'Created (\d+) tasks', result)
                                if matches:
                                    st.session_state.stats['tasks_created'] = int(matches[0])
                                    st.session_state.stats['time_saved'] += len(events) * 15  # 15 min per event
                            except:
                                pass
                        
                        # Add to sync history
                        st.session_state.sync_history.append({
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'type': 'Today\'s Events',
                            'events': len(events),
                            'result': result
                        })
                        
                        st.success("✅ Tasks created successfully!")
                else:
                    st.info("📅 No events found for today")
        
        # Custom date sync
        st.subheader("📆 Custom Date Sync")
        selected_date = st.date_input("Select Date", value=datetime.now().date())
        
        if st.button("🔄 Sync Selected Date", use_container_width=True):
            date_str = selected_date.strftime('%Y-%m-%d')
            with st.spinner(f"Fetching events for {date_str}..."):
                events = run_async(dashboard.get_calendar_events(date_str))
                
                if events:
                    st.success(f"✅ Found {len(events)} events for {date_str}!")
                    
                    with st.spinner("Creating tasks in Notion..."):
                        result = run_async(dashboard.create_notion_tasks(events))
                        st.session_state.sync_history.append({
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'type': f'Date: {date_str}',
                            'events': len(events),
                            'result': result
                        })
                        st.success("✅ Tasks created successfully!")
                else:
                    st.info(f"📅 No events found for {date_str}")
    
    # Main content
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📅 Events Today",
            value=st.session_state.stats['events_today'],
            delta=None
        )
    
    with col2:
        st.metric(
            label="✅ Tasks Created",
            value=st.session_state.stats['tasks_created'],
            delta=None
        )
    
    with col3:
        st.metric(
            label="🎯 Action Items",
            value=st.session_state.stats.get('action_items', 0),
            delta=None
        )
    
    with col4:
        st.metric(
            label="⏰ Time Saved (min)",
            value=st.session_state.stats['time_saved'],
            delta=None
        )
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Today's Events", "✅ Recent Tasks", "📊 Analytics", "📝 Sync History"])
    
    with tab1:
        st.header("📅 Today's Calendar Events")
        
        if st.session_state.events:
            for i, event in enumerate(st.session_state.events):
                with st.container():
                    st.markdown(f"""
                    <div class="event-card">
                        <h3>📅 {event.get('title', 'Untitled Event')}</h3>
                        <p><strong>🕒 Time:</strong> {event.get('start_time', 'No time specified')}</p>
                        <p><strong>📍 Location:</strong> {event.get('location', 'No location specified')}</p>
                        <p><strong>📝 Description:</strong> {event.get('description', 'No description')[:100]}{'...' if len(event.get('description', '')) > 100 else ''}</p>
                        <p><strong>👥 Attendees:</strong> {len(event.get('attendees', []))} people</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("📅 No events loaded yet. Use the sync button in the sidebar to fetch today's events.")
    
    with tab2:
        st.header("✅ Recent Tasks")
        st.info("Tasks are created in your Notion database. Check your Notion workspace to see the generated tasks!")
        
        # Show sync results
        if st.session_state.sync_history:
            latest_sync = st.session_state.sync_history[-1]
            st.markdown(f"""
            <div class="success-message">
                <h4>Latest Sync Results:</h4>
                <p><strong>Time:</strong> {latest_sync['timestamp']}</p>
                <p><strong>Type:</strong> {latest_sync['type']}</p>
                <p><strong>Events Processed:</strong> {latest_sync['events']}</p>
                <p><strong>Result:</strong> {latest_sync['result']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        st.header("📊 Analytics")
        
        if st.session_state.sync_history:
            # Create analytics charts
            df_history = pd.DataFrame(st.session_state.sync_history)
            df_history['timestamp'] = pd.to_datetime(df_history['timestamp'])
            
            # Events over time
            fig_events = px.line(
                df_history, 
                x='timestamp', 
                y='events',
                title='Events Synced Over Time',
                color_discrete_sequence=['#667eea']
            )
            st.plotly_chart(fig_events, use_container_width=True)
            
            # Sync type distribution
            fig_pie = px.pie(
                df_history, 
                names='type', 
                title='Sync Types Distribution',
                color_discrete_sequence=['#667eea', '#764ba2', '#4FC3F7']
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("📊 No sync data available yet. Perform some syncs to see analytics!")
    
    with tab4:
        st.header("📝 Sync History")
        
        if st.session_state.sync_history:
            for sync in reversed(st.session_state.sync_history):
                with st.expander(f"📅 {sync['type']} - {sync['timestamp']}"):
                    st.write(f"**Events Processed:** {sync['events']}")
                    st.write(f"**Result:** {sync['result']}")
        else:
            st.info("📝 No sync history available yet.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 1rem 0; color: #666;'>
        <p>Built with ❤️ using Streamlit, Python, Google Calendar API, Notion API, and Anthropic's MCP</p>
        <p>🚀 <strong>Deepanshu Kumar</strong> | 
        <a href='https://github.com/deepanshukr0315' target='_blank'>GitHub</a> | 
        <a href='mailto:deepanshukr0315@gmail.com'>Email</a></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()