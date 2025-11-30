#!/usr/bin/env python3
"""
Palo Alto GlobalProtect Agent Update Automation Script
This script checks and updates GlobalProtect agent software on Palo Alto firewalls
using API keys retrieved from 1Password.
"""

import json
import requests
import subprocess
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'globalprotect_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OnePasswordClient:
    """Handle 1Password CLI operations"""
    
    def __init__(self):
        self.check_op_cli()
    
    def check_op_cli(self):
        """Verify 1Password CLI is installed and configured"""
        try:
            result = subprocess.run(
                ['op', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"1Password CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("1Password CLI (op) not found. Please install it from https://1password.com/downloads/command-line/")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking 1Password CLI: {e}")
            sys.exit(1)
    
    def get_api_key(self, item_name: str, vault: str) -> Optional[str]:
        """
        Retrieve API key from 1Password vault
        
        Args:
            item_name: Name of the 1Password item
            vault: Name of the vault containing the item
            
        Returns:
            API key string or None if retrieval fails
        """
        try:
            logger.info(f"Retrieving API key for '{item_name}' from vault '{vault}'")
            
            # Use 'op item get' to retrieve the password field
            result = subprocess.run(
                ['op', 'item', 'get', item_name, '--vault', vault, '--fields', 'password'],
                capture_output=True,
                text=True,
                check=True
            )
            
            api_key = result.stdout.strip()
            if api_key:
                logger.info(f"Successfully retrieved API key for '{item_name}'")
                return api_key
            else:
                logger.error(f"Empty API key returned for '{item_name}'")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to retrieve API key for '{item_name}': {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving API key: {e}")
            return None


class PaloAltoFirewall:
    """Handle Palo Alto Firewall API operations"""
    
    def __init__(self, hostname: str, api_key: str, name: str):
        self.hostname = hostname
        self.api_key = api_key
        self.name = name
        self.base_url = f"https://{hostname}/api"
        self.session = requests.Session()
        self.session.verify = False  # Consider using proper SSL verification in production
        
    def _make_request(self, params: Dict) -> Optional[ET.Element]:
        """Make API request to firewall"""
        params['key'] = self.api_key
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            status = root.get('status')
            
            if status != 'success':
                error_msg = root.find('.//msg')
                error_text = error_msg.text if error_msg is not None else 'Unknown error'
                logger.error(f"API request failed for {self.name}: {error_text}")
                return None
                
            return root
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {self.name}: {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML response for {self.name}: {e}")
            return None
    
    def get_system_info(self) -> Optional[Dict]:
        """Get system information"""
        logger.info(f"Getting system info for {self.name}")
        
        params = {
            'type': 'op',
            'cmd': '<show><system><info></info></system></show>'
        }
        
        root = self._make_request(params)
        if root is None:
            return None
        
        result = root.find('.//result/system')
        if result is None:
            return None
        
        info = {
            'hostname': result.findtext('hostname', 'Unknown'),
            'sw_version': result.findtext('sw-version', 'Unknown'),
            'model': result.findtext('model', 'Unknown'),
            'serial': result.findtext('serial', 'Unknown')
        }
        
        return info
    
    def get_globalprotect_versions(self) -> Optional[Dict]:
        """Get available GlobalProtect client versions"""
        logger.info(f"Getting GlobalProtect versions for {self.name}")
        
        params = {
            'type': 'op',
            'cmd': '<request><global-protect-gateway><client-upgrade><list></list></client-upgrade></global-protect-gateway></request>'
        }
        
        root = self._make_request(params)
        if root is None:
            return None
        
        versions = {}
        entries = root.findall('.//entry')
        
        for entry in entries:
            version = entry.findtext('version', 'Unknown')
            os_type = entry.findtext('os', 'Unknown')
            filename = entry.findtext('filename', 'Unknown')
            
            if os_type not in versions:
                versions[os_type] = []
            
            versions[os_type].append({
                'version': version,
                'filename': filename
            })
        
        return versions
    
    def check_software_updates(self) -> Optional[Dict]:
        """Check for available software updates"""
        logger.info(f"Checking for software updates on {self.name}")
        
        params = {
            'type': 'op',
            'cmd': '<request><system><software><check></check></software></system></request>'
        }
        
        root = self._make_request(params)
        if root is None:
            return None
        
        # Wait for check to complete and get results
        time.sleep(5)
        
        params = {
            'type': 'op',
            'cmd': '<request><system><software><info></info></software></system></request>'
        }
        
        root = self._make_request(params)
        if root is None:
            return None
        
        updates = []
        entries = root.findall('.//entry')
        
        for entry in entries:
            version = entry.findtext('version', 'Unknown')
            downloaded = entry.findtext('downloaded', 'no')
            current = entry.findtext('current', 'no')
            
            updates.append({
                'version': version,
                'downloaded': downloaded == 'yes',
                'current': current == 'yes'
            })
        
        return updates
    
    def download_software(self, version: str) -> bool:
        """Download software version"""
        logger.info(f"Downloading software version {version} on {self.name}")
        
        params = {
            'type': 'op',
            'cmd': f'<request><system><software><download><version>{version}</version></download></software></system></request>'
        }
        
        root = self._make_request(params)
        return root is not None
    
    def install_software(self, version: str) -> bool:
        """Install software version"""
        logger.info(f"Installing software version {version} on {self.name}")
        
        params = {
            'type': 'op',
            'cmd': f'<request><system><software><install><version>{version}</version></install></software></system></request>'
        }
        
        root = self._make_request(params)
        return root is not None
    
    def commit_config(self) -> bool:
        """Commit configuration changes"""
        logger.info(f"Committing configuration on {self.name}")
        
        params = {
            'type': 'commit',
            'cmd': '<commit></commit>'
        }
        
        root = self._make_request(params)
        return root is not None


class GlobalProtectUpdateManager:
    """Manage GlobalProtect updates across multiple firewalls"""
    
    def __init__(self, inventory_file: str):
        self.inventory_file = inventory_file
        self.inventory = self.load_inventory()
        self.op_client = OnePasswordClient()
        self.results = []
    
    def load_inventory(self) -> Dict:
        """Load firewall inventory from JSON file"""
        try:
            with open(self.inventory_file, 'r') as f:
                inventory = json.load(f)
            logger.info(f"Loaded inventory with {len(inventory['firewalls'])} firewalls")
            return inventory
        except FileNotFoundError:
            logger.error(f"Inventory file not found: {self.inventory_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in inventory file: {e}")
            sys.exit(1)
    
    def process_firewall(self, firewall_config: Dict) -> Dict:
        """Process a single firewall"""
        result = {
            'name': firewall_config['name'],
            'hostname': firewall_config['hostname'],
            'success': False,
            'message': '',
            'system_info': None,
            'available_updates': None,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing firewall: {firewall_config['name']}")
        logger.info(f"{'='*60}")
        
        # Retrieve API key from 1Password
        api_key = self.op_client.get_api_key(
            firewall_config['onepassword_item'],
            firewall_config['onepassword_vault']
        )
        
        if not api_key:
            result['message'] = 'Failed to retrieve API key from 1Password'
            logger.error(result['message'])
            return result
        
        # Connect to firewall
        fw = PaloAltoFirewall(
            firewall_config['hostname'],
            api_key,
            firewall_config['name']
        )
        
        # Get system info
        system_info = fw.get_system_info()
        if system_info:
            result['system_info'] = system_info
            logger.info(f"Current SW version: {system_info['sw_version']}")
            logger.info(f"Model: {system_info['model']}")
        else:
            result['message'] = 'Failed to get system information'
            return result
        
        # Check for updates
        updates = fw.check_software_updates()
        if updates:
            result['available_updates'] = updates
            logger.info(f"Available updates: {len(updates)}")
            
            for update in updates:
                logger.info(f"  - Version {update['version']}: "
                          f"Downloaded={update['downloaded']}, Current={update['current']}")
        else:
            result['message'] = 'Failed to check for updates'
            return result
        
        # Get GlobalProtect client versions
        gp_versions = fw.get_globalprotect_versions()
        if gp_versions:
            logger.info("GlobalProtect client versions available:")
            for os_type, versions in gp_versions.items():
                logger.info(f"  {os_type}: {len(versions)} versions")
        
        result['success'] = True
        result['message'] = 'Successfully checked firewall'
        
        return result
    
    def run(self):
        """Run the update check/process for all firewalls"""
        logger.info("Starting GlobalProtect update automation")
        logger.info(f"Processing {len(self.inventory['firewalls'])} firewalls")
        
        # Disable SSL warnings (consider proper SSL verification in production)
        requests.packages.urllib3.disable_warnings()
        
        for fw_config in self.inventory['firewalls']:
            if not fw_config.get('enabled', True):
                logger.info(f"Skipping disabled firewall: {fw_config['name']}")
                continue
            
            result = self.process_firewall(fw_config)
            self.results.append(result)
        
        self.generate_report()
    
    def generate_report(self):
        """Generate summary report"""
        logger.info("\n" + "="*60)
        logger.info("SUMMARY REPORT")
        logger.info("="*60)
        
        successful = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - successful
        
        logger.info(f"Total firewalls processed: {len(self.results)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        
        # Save detailed report
        report_file = f'update_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"\nDetailed report saved to: {report_file}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Automate GlobalProtect agent updates on Palo Alto firewalls'
    )
    parser.add_argument(
        '--inventory',
        default='firewall_inventory.json',
        help='Path to firewall inventory file (default: firewall_inventory.json)'
    )
    
    args = parser.parse_args()
    
    manager = GlobalProtectUpdateManager(args.inventory)
    manager.run()


if __name__ == '__main__':
    main()
