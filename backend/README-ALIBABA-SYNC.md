# Alibaba Message Sync System

This is a production-ready automated message synchronization system for Alibaba.com that performs initial sync going back 1 week, then syncs new messages every 5 minutes.

## Features

- **Automated Authentication**: Browser automation with 2FA support via IMAP email integration
- **Initial Sync**: Syncs messages from the past week on first run
- **Incremental Sync**: Checks for new messages every 5 minutes
- **Database Integration**: Stores messages, chats, and profiles in the existing database
- **Error Handling**: Robust error handling with retry logic and exponential backoff
- **Monitoring**: Comprehensive logging and health checks
- **Production Ready**: Docker deployment, systemd service, graceful shutdown

## Architecture

```
┌─────────────────┐    ┌────────────────┐    ┌─────────────────┐
│   Scheduler     │───▶│  Sync Service  │───▶│ Production      │
│   (5 min loop)  │    │                │    │ Adapter         │
└─────────────────┘    └────────────────┘    └─────────────────┘
                                                       │
                       ┌────────────────┐              │
                       │   Database     │◀─────────────┘
                       │   (Messages,   │
                       │   Chats,       │
                       │   Profiles)    │
                       └────────────────┘
                                │
                       ┌────────────────┐
                       │   Email 2FA    │
                       │   (IMAP)       │
                       └────────────────┘
```

## Quick Start

### 1. Environment Setup

Copy the environment template:
```bash
cp .env.alibaba.template .env.alibaba
```

Edit `.env.alibaba` with your credentials:
```bash
# Required
ALIBABA_USERNAME=your-username@email.com
ALIBABA_PASSWORD=your-password
EMAIL_PASSWORD=your-email-app-password
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Optional
SYNC_INTERVAL_MINUTES=5
LOG_LEVEL=INFO
```

### 2. Docker Deployment (Recommended)

```bash
# Start the service
docker-compose -f docker-compose.alibaba.yml up -d

# View logs
docker-compose -f docker-compose.alibaba.yml logs -f alibaba-sync

# Stop the service
docker-compose -f docker-compose.alibaba.yml down
```

### 3. Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run initial sync
python tools/alibaba_sync_manager.py initial --days 7

# Start scheduler
python tools/alibaba_sync_manager.py scheduler --interval 5
```

### 4. Systemd Service

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

### Authentication Flow

1. **Browser Automation**: Uses Playwright with stealth settings to avoid detection
2. **Login Form**: Automatically fills username and password
3. **2FA Detection**: Detects when 2FA verification is required
4. **Email Retrieval**: Connects to email via IMAP to retrieve 2FA codes
5. **Coordinate Clicking**: Uses precise coordinates to fill verification code
6. **Session Persistence**: Saves browser state for future use

### Sync Process

#### Initial Sync
- Runs on first startup or when account hasn't been synced in 24+ hours
- Retrieves conversations from the past week (configurable)
- Creates database records for:
  - Profiles (conversation participants)
  - Chats (conversations)
  - Messages (message content)

#### Incremental Sync
- Runs every 5 minutes (configurable)
- Checks existing chats for new messages since last sync
- Discovers new conversations
- Updates database with new content only

### Database Schema

The system integrates with existing models:

- **PlatformAccount**: Alibaba account credentials and sync status
- **Profile**: Conversation participants (e.g., "Linda Wu")
- **Chat**: Individual conversations/threads
- **Message**: Individual messages with content, timestamps, direction

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALIBABA_USERNAME` | Alibaba login email | Required |
| `ALIBABA_PASSWORD` | Alibaba login password | Required |
| `EMAIL_PASSWORD` | Email app password for 2FA | Required |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SYNC_INTERVAL_MINUTES` | Minutes between syncs | 5 |
| `LOG_LEVEL` | Logging level | INFO |
| `RATE_LIMIT_INITIAL_DELAY` | Initial retry delay (seconds) | 60 |
| `RATE_LIMIT_BACKOFF_FACTOR` | Exponential backoff factor | 2 |
| `RATE_LIMIT_MAX_DELAY` | Maximum retry delay (seconds) | 3600 |

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