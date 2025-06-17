# Alibaba Message Sync System

This is a production-ready automated message synchronization system for Alibaba.com that captures conversation history and syncs new messages.

## Features

- **Long-Running Browser Adapter**: Persistent browser context with cookie persistence
- **Automated Authentication**: Browser automation with 2FA support via IMAP email integration  
- **Message Extraction**: Advanced DOM parsing with JavaScript data extraction
- **Message Deduplication**: Content-based deduplication using hashing
- **Reply Detection**: Framework for detecting quoted/threaded messages
- **Database Integration**: Stores messages, chats, and profiles with reply tracking
- **Error Handling**: Robust error handling with retry logic
- **Monitoring**: Comprehensive logging and health checks

## Architecture

```
┌─────────────────┐    ┌────────────────┐    ┌─────────────────┐
│   Scheduler     │───▶│  Sync Service  │───▶│ Long-Running    │
│   (Periodic)    │    │                │    │ Adapter         │
└─────────────────┘    └────────────────┘    └─────────────────┘
                                                       │
                       ┌────────────────┐              │
                       │   Database     │◀─────────────┘
                       │   (Messages,   │              │
                       │   Chats,       │              │
                       │   Profiles,    │              │
                       │   Reply Data)  │              │
                       └────────────────┘              │
                                │                      │
                       ┌────────────────┐              │
                       │   Email 2FA    │              │
                       │   (IMAP)       │              │
                       └────────────────┘              │
                                                       │
                       ┌────────────────┐              │
                       │ Message Parser │◀─────────────┘
                       │ (Deduplication,│
                       │  Reply Detect) │
                       └────────────────┘
```

## Quick Start

### 1. Environment Setup

Set up your environment variables:
```bash
# Required
export ALIBABA_USERNAME=your-username@email.com
export ALIBABA_PASSWORD=your-password
export EMAIL_PASSWORD=your-email-app-password
export DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Optional
export BROWSER_HEADLESS=true
export EMAIL_2FA_FOLDER=2FA
export LOG_LEVEL=INFO
```

### 2. Installation

```bash
# Install dependencies
pip install -r requirements-alibaba.txt
playwright install chromium

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-alibaba.txt
```

### 3. Database Setup

```bash
# The system will automatically add required columns for reply tracking
# No manual migration needed - it uses ALTER TABLE IF NOT EXISTS
```

### 4. Running the System

```bash
# Run initial sync to capture past 7 days
python tools/alibaba_sync_manager.py initial --days 7

# Start periodic scheduler
python tools/alibaba_sync_manager.py scheduler --interval 5
```

### 5. Optional: Systemd Service

```bash
# Copy service file
sudo cp scripts/alibaba-sync.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/alibaba-sync.service

# Enable and start
sudo systemctl enable alibaba-sync
sudo systemctl start alibaba-sync

# Check status
sudo systemctl status alibaba-sync
```

## Management Commands

The `alibaba_sync_manager.py` tool provides comprehensive management:

```bash
# Show all accounts
python tools/alibaba_sync_manager.py accounts

# Run initial sync (7 days back)
python tools/alibaba_sync_manager.py initial

# Run incremental sync
python tools/alibaba_sync_manager.py incremental

# Start scheduler
python tools/alibaba_sync_manager.py scheduler --interval 5

# Show statistics
python tools/alibaba_sync_manager.py stats

# Account-specific operations
python tools/alibaba_sync_manager.py initial --account ACCOUNT_ID
python tools/alibaba_sync_manager.py stats --account ACCOUNT_ID
```

## How It Works

### Long-Running Browser Adapter

The system uses a persistent browser context that stays open between syncs:

1. **Persistent Context**: Browser maintains session state and cookies
2. **Cookie Persistence**: Session data saved to disk for reuse
3. **Conversation Navigation**: Automatically clicks through conversation tabs
4. **Message Extraction**: Uses DOM parsing and JavaScript data extraction

### Authentication Flow

1. **Browser Automation**: Uses Playwright with stealth settings to avoid detection
2. **Session Reuse**: Attempts to use saved cookies first
3. **Login Form**: Automatically fills username and password if needed
4. **2FA Detection**: Detects when 2FA verification is required
5. **Email Retrieval**: Connects to email via IMAP to retrieve 2FA codes (auto-filters to 2FA folder)
6. **Coordinate Clicking**: Uses precise coordinates (730,360) to fill verification code
7. **Session Persistence**: Saves browser state for future use

### Message Extraction

1. **Conversation Detection**: Finds conversation elements using CSS selectors
2. **DOM Parsing**: Extracts message content from DOM elements
3. **JavaScript Extraction**: Parses JSON data embedded in page JavaScript
4. **Content Cleaning**: Removes UI elements, duplicates, and artifacts
5. **Deduplication**: Uses content hashing to prevent duplicate messages
6. **Reply Detection**: Framework to identify quoted/threaded messages

### Database Schema

The system extends existing models with reply tracking:

- **PlatformAccount**: Alibaba account credentials and sync status
- **Profile**: Conversation participants (e.g., "Linda Wu")
- **Chat**: Individual conversations/threads
- **Message**: Individual messages with content, timestamps, direction, reply tracking
  - `is_reply`: Boolean flag for reply messages
  - `reply_to_content`: Content of the message being replied to

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALIBABA_USERNAME` | Alibaba login email | Required |
| `ALIBABA_PASSWORD` | Alibaba login password | Required |
| `EMAIL_PASSWORD` | Email app password for 2FA | Required |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `BROWSER_HEADLESS` | Run browser in headless mode | true |
| `EMAIL_2FA_FOLDER` | Email folder for 2FA codes | 2FA |
| `LOG_LEVEL` | Logging level | INFO |

### Email Setup

For 2FA to work, you need an app password for your email:

**Fastmail:**
1. Go to Settings > Password & Security
2. Create a new app password
3. Use this password in `EMAIL_PASSWORD`

**Gmail:**
1. Enable 2FA on your Google account
2. Go to App passwords
3. Generate a new app password
4. Use this password in `EMAIL_PASSWORD`

## Monitoring

### Logs

The system provides comprehensive logging:

```bash
# Docker logs
docker-compose logs -f alibaba-sync

# File logs (if configured)
tail -f logs/alibaba_scheduler.log

# Systemd logs
journalctl -u alibaba-sync -f
```

### Health Checks

Monitor sync health:

```bash
# Check last sync times
python tools/alibaba_sync_manager.py stats

# Database queries
psql -d grand_central_station -c "
  SELECT 
    pa.username,
    pa.last_sync,
    pa.error_count,
    COUNT(c.id) as chat_count,
    COUNT(m.id) as message_count
  FROM platform_accounts pa
  LEFT JOIN chats c ON c.account_id = pa.id  
  LEFT JOIN messages m ON m.chat_id = c.id
  WHERE pa.platform_id = (SELECT id FROM platforms WHERE name = 'alibaba')
  GROUP BY pa.id, pa.username, pa.last_sync, pa.error_count;
"
```

### Metrics

Key metrics to monitor:

- **Sync Success Rate**: `error_count` should remain low
- **Message Volume**: New messages per sync cycle
- **Sync Latency**: Time between message receipt and sync
- **Authentication Success**: 2FA code retrieval success rate

## Troubleshooting

### Common Issues

**Authentication Failures:**
- Check username/password in environment
- Verify email app password is correct
- Check if Alibaba account is locked/requires manual verification

**2FA Issues:**
- Ensure email credentials are correct
- Check if 2FA emails are being received
- Verify IMAP is enabled on email account

**Sync Failures:**
- Check database connectivity
- Monitor for bot detection (502/403 errors)
- Verify browser automation isn't blocked

**Performance Issues:**
- Monitor memory usage (browser can be memory-intensive)
- Check database query performance
- Adjust sync interval if needed

### Debug Mode

Run with debug logging:

```bash
python tools/alibaba_sync_manager.py scheduler --log-level DEBUG
```

Enable browser visibility:

```python
# In alibaba_production.py, set headless=False
await self.init_browser(headless=False)
```

## Security Considerations

- **Credentials**: Store credentials securely using environment variables
- **Network**: Use VPN if running on cloud infrastructure
- **Rate Limiting**: Respect Alibaba's rate limits to avoid detection
- **Browser Fingerprinting**: Uses realistic browser settings to avoid detection
- **2FA**: Secure email integration for automated 2FA handling

## Scaling

For multiple accounts:

1. **Separate Instances**: Run one scheduler per account
2. **Database Sharding**: Partition by account if needed
3. **Load Balancing**: Distribute across multiple servers
4. **Queue System**: Use Redis/RabbitMQ for job distribution

## License

This system is part of the Grand Central Station project.