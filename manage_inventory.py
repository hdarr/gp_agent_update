#!/usr/bin/env python3
"""
Helper script to manage firewall inventory
"""

import json
import sys
from typing import Dict, List

INVENTORY_FILE = 'firewall_inventory.json'


def load_inventory() -> Dict:
    """Load inventory from file"""
    try:
        with open(INVENTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'firewalls': [],
            'settings': {
                'check_interval_days': 7,
                'backup_before_update': True,
                'auto_commit': False,
                'notification_email': 'firewall-admin@example.com'
            }
        }


def save_inventory(inventory: Dict):
    """Save inventory to file"""
    with open(INVENTORY_FILE, 'w') as f:
        json.dump(inventory, f, indent=2)
    print(f"Inventory saved to {INVENTORY_FILE}")


def list_firewalls(inventory: Dict):
    """List all firewalls"""
    if not inventory['firewalls']:
        print("No firewalls in inventory")
        return
    
    print(f"\n{'Name':<20} {'Hostname':<30} {'Enabled':<10} {'Location':<20}")
    print("-" * 80)
    
    for fw in inventory['firewalls']:
        enabled = "Yes" if fw.get('enabled', True) else "No"
        location = fw.get('location', 'N/A')
        print(f"{fw['name']:<20} {fw['hostname']:<30} {enabled:<10} {location:<20}")
    
    print(f"\nTotal firewalls: {len(inventory['firewalls'])}")


def add_firewall(inventory: Dict):
    """Add a new firewall"""
    print("\n=== Add New Firewall ===")
    
    name = input("Firewall name: ").strip()
    if not name:
        print("Error: Name is required")
        return
    
    # Check for duplicate name
    if any(fw['name'] == name for fw in inventory['firewalls']):
        print(f"Error: Firewall '{name}' already exists")
        return
    
    hostname = input("Hostname/IP: ").strip()
    if not hostname:
        print("Error: Hostname is required")
        return
    
    ip = input("IP address (optional): ").strip()
    location = input("Location (optional): ").strip()
    model = input("Model (optional): ").strip()
    
    print("\n1Password Configuration:")
    op_item = input("1Password item name: ").strip()
    if not op_item:
        print("Error: 1Password item name is required")
        return
    
    op_vault = input("1Password vault name: ").strip()
    if not op_vault:
        print("Error: 1Password vault name is required")
        return
    
    firewall = {
        'name': name,
        'hostname': hostname,
        'onepassword_item': op_item,
        'onepassword_vault': op_vault,
        'enabled': True
    }
    
    if ip:
        firewall['ip'] = ip
    if location:
        firewall['location'] = location
    if model:
        firewall['model'] = model
    
    inventory['firewalls'].append(firewall)
    save_inventory(inventory)
    print(f"\nFirewall '{name}' added successfully")


def remove_firewall(inventory: Dict):
    """Remove a firewall"""
    list_firewalls(inventory)
    
    if not inventory['firewalls']:
        return
    
    name = input("\nEnter firewall name to remove: ").strip()
    
    for i, fw in enumerate(inventory['firewalls']):
        if fw['name'] == name:
            confirm = input(f"Are you sure you want to remove '{name}'? (yes/no): ").lower()
            if confirm == 'yes':
                inventory['firewalls'].pop(i)
                save_inventory(inventory)
                print(f"Firewall '{name}' removed successfully")
            else:
                print("Removal cancelled")
            return
    
    print(f"Firewall '{name}' not found")


def enable_disable_firewall(inventory: Dict, enable: bool):
    """Enable or disable a firewall"""
    list_firewalls(inventory)
    
    if not inventory['firewalls']:
        return
    
    action = "enable" if enable else "disable"
    name = input(f"\nEnter firewall name to {action}: ").strip()
    
    for fw in inventory['firewalls']:
        if fw['name'] == name:
            fw['enabled'] = enable
            save_inventory(inventory)
            print(f"Firewall '{name}' {action}d successfully")
            return
    
    print(f"Firewall '{name}' not found")


def update_settings(inventory: Dict):
    """Update global settings"""
    print("\n=== Current Settings ===")
    for key, value in inventory['settings'].items():
        print(f"{key}: {value}")
    
    print("\n1. Check interval (days)")
    print("2. Backup before update")
    print("3. Auto commit")
    print("4. Notification email")
    print("5. Back to main menu")
    
    choice = input("\nSelect setting to update: ").strip()
    
    if choice == '1':
        days = input("Enter check interval in days: ").strip()
        try:
            inventory['settings']['check_interval_days'] = int(days)
            save_inventory(inventory)
        except ValueError:
            print("Invalid number")
    
    elif choice == '2':
        value = input("Backup before update? (yes/no): ").lower()
        inventory['settings']['backup_before_update'] = value == 'yes'
        save_inventory(inventory)
    
    elif choice == '3':
        value = input("Auto commit? (yes/no): ").lower()
        inventory['settings']['auto_commit'] = value == 'yes'
        save_inventory(inventory)
    
    elif choice == '4':
        email = input("Notification email: ").strip()
        if email:
            inventory['settings']['notification_email'] = email
            save_inventory(inventory)


def main_menu():
    """Display main menu"""
    while True:
        print("\n" + "="*50)
        print("Firewall Inventory Manager")
        print("="*50)
        print("1. List firewalls")
        print("2. Add firewall")
        print("3. Remove firewall")
        print("4. Enable firewall")
        print("5. Disable firewall")
        print("6. Update settings")
        print("7. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        inventory = load_inventory()
        
        if choice == '1':
            list_firewalls(inventory)
        elif choice == '2':
            add_firewall(inventory)
        elif choice == '3':
            remove_firewall(inventory)
        elif choice == '4':
            enable_disable_firewall(inventory, True)
        elif choice == '5':
            enable_disable_firewall(inventory, False)
        elif choice == '6':
            update_settings(inventory)
        elif choice == '7':
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option")


if __name__ == '__main__':
    main_menu()
