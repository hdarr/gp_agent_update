# GlobalProtect Agent Update

Automated script to check and update GlobalProtect agent software on Palo Alto firewalls using API keys stored in 1Password.

## Features

- **1Password Integration**: Securely retrieves API keys from 1Password vaults
- **Inventory Management**: JSON-based inventory file for easy firewall management
- **Comprehensive Logging**: Detailed logs with timestamps for audit trails
- **System Information**: Retrieves current software versions and system details
- **Update Checking**: Checks for available software updates
- **GlobalProtect Versions**: Lists available GlobalProtect client versions
- **JSON Reports**: Generates detailed JSON reports of all operations

## Prerequisites

### 1. Install 1Password CLI

```bash
# macOS
brew install --cask 1password-cli

# Linux
curl -sS https://downloads.1password.com/linux/keys/1password.asc | \
  sudo gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] \
  https://downloads.1password.com/linux/debian/$(dpkg --print-architecture) stable main" | \
  sudo tee /etc/apt/sources.list.d/1password.list
sudo apt update && sudo apt install 1password-cli

# Windows
# Download from https://1password.com/downloads/command-line/
```

### 2. Authenticate with 1Password

```bash
# Sign in to 1Password
op signin

# Or use service account token
export OP_SERVICE_ACCOUNT_TOKEN="your-service-account-token"
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 1Password Setup

### Store API Keys in 1Password

For each firewall, create an item in 1Password with:
- **Item Name**: e.g., "PA Firewall HQ-01 API Key"
- **Vault**: e.g., "Infrastructure"
- **Password Field**: The API key from the firewall

### Generate API Key on Palo Alto Firewall

1. Log into the firewall web interface
2. Navigate to: **Device > Administrators**
3. Select an admin user or create a new one
4. Under **Administrator Type**, select "Role Based"
5. Assign appropriate roles (minimum: Device Admin)
6. Generate API key using XML API:
   ```bash
   curl.exe -k 'https://<firewall>/api/?type=keygen&user=<username>&password=<password>'
   ```
7. Store the API key in 1Password

## Configuration

### Inventory File (`firewall_inventory.json`)

```json
{
  "firewalls": [
    {
      "name": "fw-hq-01",
      "hostname": "firewall1.example.com",
      "ip": "10.0.1.10",
      "onepassword_item": "PA Firewall HQ-01 API Key",
      "onepassword_vault": "Infrastructure",
      "enabled": true,
      "location": "Headquarters",
      "model": "PA-5220"
    }
  ],
  "settings": {
    "check_interval_days": 7,
    "backup_before_update": true,
    "auto_commit": false,
    "notification_email": "firewall-admin@example.com"
  }
}
```

### Inventory Fields

- **name**: Friendly name for the firewall
- **hostname**: FQDN or IP address
- **ip**: IP address (for reference)
- **onepassword_item**: Name of the 1Password item containing the API key
- **onepassword_vault**: 1Password vault name
- **enabled**: Set to `false` to skip this firewall
- **location**: Physical location (optional, for reference)
- **model**: Firewall model (optional, for reference)

## Usage

### Basic Usage

```bash
# Make the script executable
chmod +x globalprotect_update.py

# Run with default inventory file
./globalprotect_update.py

# Run with custom inventory file
./globalprotect_update.py --inventory /path/to/custom_inventory.json
```

### Example Output

```
2024-11-27 10:30:15 - INFO - Starting GlobalProtect update automation
2024-11-27 10:30:15 - INFO - Loaded inventory with 3 firewalls
2024-11-27 10:30:15 - INFO - Processing 3 firewalls
============================================================
Processing firewall: fw-hq-01
============================================================
2024-11-27 10:30:16 - INFO - Retrieving API key for 'PA Firewall HQ-01 API Key' from vault 'Infrastructure'
2024-11-27 10:30:17 - INFO - Successfully retrieved API key for 'PA Firewall HQ-01 API Key'
2024-11-27 10:30:18 - INFO - Getting system info for fw-hq-01
2024-11-27 10:30:19 - INFO - Current SW version: 10.2.3
2024-11-27 10:30:19 - INFO - Model: PA-5220
2024-11-27 10:30:20 - INFO - Checking for software updates on fw-hq-01
2024-11-27 10:30:26 - INFO - Available updates: 2
2024-11-27 10:30:26 - INFO -   - Version 10.2.4: Downloaded=False, Current=False
2024-11-27 10:30:26 - INFO -   - Version 11.0.0: Downloaded=False, Current=False
```

## Script Features

### 1. OnePasswordClient Class

Handles all 1Password CLI interactions:
- Verifies 1Password CLI installation
- Retrieves API keys from specified vaults
- Error handling for authentication issues

### 2. PaloAltoFirewall Class

Manages firewall API operations:
- **get_system_info()**: Retrieves system information
- **get_globalprotect_versions()**: Lists available GlobalProtect client versions
- **check_software_updates()**: Checks for available software updates
- **download_software()**: Downloads a specific software version
- **install_software()**: Installs a software version
- **commit_config()**: Commits configuration changes

### 3. GlobalProtectUpdateManager Class

Orchestrates the entire update process:
- Loads inventory file
- Processes each firewall
- Generates reports
- Handles errors gracefully

## Output Files

### Log Files

- **Format**: `globalprotect_update_YYYYMMDD_HHMMSS.log`
- **Content**: Detailed operation logs with timestamps

### Report Files

- **Format**: `update_report_YYYYMMDD_HHMMSS.json`
- **Content**: JSON report with results for each firewall

```json
[
  {
    "name": "fw-hq-01",
    "hostname": "firewall1.example.com",
    "success": true,
    "message": "Successfully checked firewall",
    "system_info": {
      "hostname": "PA-FW-HQ-01",
      "sw_version": "10.2.3",
      "model": "PA-5220",
      "serial": "012345678901"
    },
    "available_updates": [
      {
        "version": "10.2.4",
        "downloaded": false,
        "current": false
      }
    ],
    "timestamp": "2024-11-27T10:30:26"
  }
]
```

## Security Considerations

1. **API Key Storage**: API keys are stored in 1Password, not in the script or inventory file
2. **SSL Verification**: Currently disabled for testing; enable in production:
   ```python
   self.session.verify = True  # or provide path to CA bundle
   ```
3. **Permissions**: Ensure the script runs with appropriate user permissions
4. **Audit Logs**: All operations are logged for audit purposes
5. **Service Accounts**: Consider using 1Password service accounts for automation

## Extending the Script

### Adding Software Download/Install

To enable automatic download and installation, modify the `process_firewall` method:

```python
# Check if updates are available
if updates and not all(u['current'] for u in updates):
    latest_update = max(updates, key=lambda x: x['version'])
    
    if not latest_update['downloaded']:
        logger.info(f"Downloading version {latest_update['version']}")
        fw.download_software(latest_update['version'])
    
    if self.inventory['settings'].get('auto_commit', False):
        logger.info("Installing and committing")
        fw.install_software(latest_update['version'])
        fw.commit_config()
```

### Adding Email Notifications

Integrate with your email system:

```python
import smtplib
from email.mime.text import MIMEText

def send_notification(self, report):
    msg = MIMEText(json.dumps(report, indent=2))
    msg['Subject'] = 'GlobalProtect Update Report'
    msg['From'] = 'automation@example.com'
    msg['To'] = self.inventory['settings']['notification_email']
    
    # Send email
    # ... SMTP configuration
```

## Troubleshooting

### 1Password CLI Issues

```bash
# Check if op CLI is installed
op --version

# Test authentication
op item list --vault Infrastructure

# Re-authenticate if needed
op signin
```

### Firewall Connection Issues

- Verify hostname/IP is correct
- Check firewall API access is enabled
- Verify API key is valid
- Check network connectivity
- Review firewall logs

### SSL Certificate Errors

For production, use proper SSL verification:

```python
# Option 1: Use system CA bundle
self.session.verify = True

# Option 2: Use custom CA bundle
self.session.verify = '/path/to/ca-bundle.crt'
```

## Best Practices

1. **Test First**: Run on a test firewall before production
2. **Backup**: Always backup configurations before updates
3. **Scheduling**: Use cron or Task Scheduler for automated runs
4. **Monitoring**: Monitor logs and reports regularly
5. **Maintenance Windows**: Schedule updates during maintenance windows
6. **Rollback Plan**: Have a rollback plan ready

## Cron Example

```bash
# Run every Sunday at 2 AM
0 2 * * 0 /usr/bin/python3 /path/to/globalprotect_update.py --inventory /path/to/inventory.json
```

## Support

For issues or questions:
1. Check the log files for detailed error messages
2. Verify 1Password CLI authentication
3. Test firewall API connectivity manually
4. Review Palo Alto API documentation

## License

This script is provided as-is for automation purposes.
