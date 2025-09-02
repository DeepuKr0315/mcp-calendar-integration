
# Calendar to Notion MCP Integration

Automatically sync your Google Calendar events to Notion tasks with AI-powered action item extraction using Anthropic's Model Context Protocol (MCP).

## Features

- 📅 **Google Calendar Integration** - Fetch daily or date-specific events
- 📝 **Notion Task Creation** - Convert events to organized tasks
- 🎯 **Action Item Extraction** - Automatically extract action items from meeting descriptions
- 📊 **Meeting Summaries** - Generate detailed meeting summaries with action items
- 🔄 **Automated Workflow** - One-click sync from calendar to tasks

## Prerequisites

- Python 3.8+
- Google Calendar API access
- Notion API integration
- Notion database with required properties

## Setup

### 1. Clone the Repository
```
git clone https://github.com/deepanshukr0315/calendar-notion-mcp-sync.git
cd calendar-notion-mcp-sync
```

### 2. Create Virtual Environment
```
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```
pip install -r requirements.txt
```

### 4. Google Calendar API Setup

1. Go to Google Cloud Console
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials JSON file as credentials.json
6. Add your email as a test user in OAuth consent screen

### 5. Notion API Setup

1. Go to Notion Developers
2. Create new integration
3. Copy the API key
4. Create a database with these properties:
 - Name (Title)
 - Status (Select: Not started, In progress, Done)
 - Priority (Select: High, Medium, Low)
 - Source (Select: Calendar, Meeting)
 - Due Date (Date)
 - Created (Date)
5. Share the database with your integration

### 6. Environment Configuration
Create .env file in project root:
```
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_notion_database_id_here
```

## Usage
### Interactive Workflow
`python calendar_to_notion_workflow.py`

* Choose from:

1. **Sync today's events** - Process today's calendar events
2. **Sync specific date** - Process events from any date
3. **Test connections** - Verify both servers work

### Individual Servers

* **Calendar Server**:
`python src/calendar_server.py`

* **Notion Server**:
`python src/notion_server.py`

* **Test Calendar Integration**:
`Test Calendar Integration:`

## MCP Tools Available

### Calendar Server Tools
* `get_todays_events` - Fetch today's calendar events
* `get_events_by_date` - Get events for specific date
* `extract_meeting_details` - Extract action items from text

### Notion Server Tools
* `create_task` - Create individual task
* `create_tasks_from_calendar_events` - Bulk convert events to tasks
* `create_meeting_summary` - Create detailed meeting summary
* `get_tasks` - Retrieve existing tasks

## Project Structure

```
calendar-notion-mcp-sync/
├── src/
│   ├── calendar_server.py      # Google Calendar MCP server
│   ├── notion_server.py        # Notion API MCP server
│   └── config.py              # Configuration management
├── calendar_to_notion_workflow.py  # Main integration workflow
├── test_calendar_client.py    # Calendar server testing
├── credentials.json           # Google OAuth credentials (not in repo)
├── .env                      # Environment variables (not in repo)
├── .env.example             # Environment template
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## How It Works

1. **Calendar Fetch**: Retrieves events from Google Calendar for specified date
2. **Event Processing**: Analyzes event descriptions for action items
3. **Task Creation**: Creates structured tasks in Notion with:
   * Event details as main task
   * Extracted action items as high-priority sub-tasks
   * Meeting summaries for complex events
4. **Smart Categorization**: Automatically assigns priorities and sources

### Example Output

```
📅 Found 3 calendar events
✅ Created 8 tasks from calendar events:
- Event: Team Standup
- Action: Review budget report
- Action: Contact vendor for pricing
- Event: Client Meeting
- Action: Prepare proposal
- Action: Schedule follow-up
- Event: Project Review
- Meeting Summary: Project Review
```

## Troubleshooting
### Google Calendar Issues
* Ensure OAuth consent screen has your email as test user
* Check `credentials.json` is valid and in project root
* Verify Google Calendar API is enabled
### Notion Issues
* Confirm API key has correct permissions
* Verify database ID is correct
* Check database properties match required schema
### MCP Server Issues
* Ensure virtual environment is activated
* Check all dependencies are installed
* Verify `.env` file format is correct
### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.
Acknowledgments
* Built with [Anthropic's MCP](https://docs.anthropic.com/en/docs/build-with-claude/mcp)
* Google Calendar API
* Notion API
* Python MCP SDK

## Author
**Deepanshu Kumar** - [GitHub](https://github.com/deepanshukr0315) - [Email](mailto:deepanshukr0315@gmail.com)

## Support
For support, please open an issue in the GitHub repository.
---
⭐ If you found this project helpful, please give it a star! EOF

```