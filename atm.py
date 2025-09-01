#!/usr/bin/env python3
"""
ATM program
This is my first ATM program
"""

import json
import os
import hashlib
import secrets
import getpass
import time
import sys

# file to save data
DB_FILE = "db.json"

def load_db():
    """load database"""
    if not os.path.exists(DB_FILE):
        # make new database
        new_db = {"atm_cash": 10000, "users": {}, "transactions": []}
        save_db(new_db)
        return new_db
    
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    """save database"""
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def hash_pin(pin, salt=None):
    """hash pin"""
    if salt is None:
        salt = secrets.token_hex(8)
    
    pin_hash = hashlib.sha256((salt + pin).encode()).hexdigest()
    return salt, pin_hash

def verify_pin(pin, salt, pin_hash):
    """check pin"""
    return hashlib.sha256((salt + pin).encode()).hexdigest() == pin_hash

def log_transaction(db, username, action_type, amount, note=""):
    """save transaction"""
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user": username,
        "type": action_type,
        "amount": amount,
        "note": note
    }
    db["transactions"].append(entry)
    save_db(db)

def create_user(db, username, pin, role="user", balance=0):
    """create user"""
    if username in db["users"]:
        raise ValueError("user exists")
    
    salt, pin_hash = hash_pin(pin)
    db["users"][username] = {
        "role": role,
        "pin_salt": salt,
        "pin_hash": pin_hash,
        "balance": float(balance)
    }
    save_db(db)
    log_transaction(db, username, "create_user", balance, f"role={role}")

def delete_user(db, username):
    """delete user"""
    if username not in db["users"]:
        raise ValueError("no user")
    
    del db["users"][username]
    save_db(db)
    log_transaction(db, username, "delete_user", 0, "deleted")

def change_pin(db, username, old_pin, new_pin):
    """change pin"""
    user = db["users"].get(username)
    if not user:
        raise ValueError("no user")
    
    if not verify_pin(old_pin, user["pin_salt"], user["pin_hash"]):
        raise ValueError("wrong pin")
    
    salt, pin_hash = hash_pin(new_pin)
    user["pin_salt"] = salt
    user["pin_hash"] = pin_hash
    save_db(db)
    log_transaction(db, username, "change_pin", 0, "")

def check_balance(db, username):
    """get balance"""
    user = db["users"].get(username)
    if not user:
        raise ValueError("no user")
    return user["balance"]

def deposit(db, username, amount):
    """deposit money"""
    if amount <= 0:
        raise ValueError("bad amount")
    
    user = db["users"].get(username)
    if not user:
        raise ValueError("no user")
    
    user["balance"] += amount
    db["atm_cash"] += amount
    save_db(db)
    log_transaction(db, username, "deposit", amount, "")

def withdraw(db, username, amount):
    """withdraw money"""
    if amount <= 0:
        raise ValueError("bad amount")
    
    user = db["users"].get(username)
    if not user:
        raise ValueError("no user")
    
    if user["balance"] < amount:
        raise ValueError("no money")
    
    if db["atm_cash"] < amount:
        raise ValueError("no cash")
    
    user["balance"] -= amount
    db["atm_cash"] -= amount
    save_db(db)
    log_transaction(db, username, "withdraw", amount, "")
    return True

def list_users(db):
    """show users"""
    summary = {}
    for username, info in db["users"].items():
        summary[username] = {"role": info["role"], "balance": info["balance"]}
    return summary

def view_transactions(db, limit=20):
    """show transactions"""
    return db["transactions"][-limit:]

def set_atm_cash(db, amount):
    """set cash"""
    db["atm_cash"] = float(amount)
    save_db(db)
    log_transaction(db, "admin", "set_atm_cash", amount, "")

def authenticate(db, username):
    """login"""
    if username not in db["users"]:
        print("no user")
        return False
    
    user = db["users"][username]
    pin = getpass.getpass("PIN: ")
    
    if verify_pin(pin, user["pin_salt"], user["pin_hash"]):
        return True
    else:
        print("wrong pin")
        return False

def admin_menu(db, admin_username):
    """admin menu"""
    while True:
        print("\nADMIN MENU")
        print("1) users")
        print("2) create user")
        print("3) delete user")
        print("4) transactions")
        print("5) set cash")
        print("6) exit")
        
        choice = input("choice: ")
        
        try:
            if choice == "1":
                users = list_users(db)
                for username, info in users.items():
                    print(f"{username}: {info['role']}, {info['balance']}")
                    
            elif choice == "2":
                username = input("username: ")
                pin = getpass.getpass("pin: ")
                role = input("role (user): ") or "user"
                balance = float(input("balance (0): ") or 0)
                create_user(db, username, pin, role, balance)
                print("created")
                
            elif choice == "3":
                username = input("username: ")
                confirm = input("delete? (yes): ")
                if confirm == "yes":
                    delete_user(db, username)
                    print("deleted")
                    
            elif choice == "4":
                transactions = view_transactions(db, 20)
                for tx in transactions:
                    print(tx)
                    
            elif choice == "5":
                amount = float(input("cash: "))
                set_atm_cash(db, amount)
                print("done")
                
            elif choice == "6":
                break
            else:
                print("bad choice")
                
        except Exception as e:
            print("error:", e)

def user_menu(db, username):
    """user menu"""
    while True:
        print(f"\nUSER MENU - {username}")
        print("1) balance")
        print("2) withdraw")
        print("3) deposit")
        print("4) change pin")
        print("5) exit")
        
        choice = input("choice: ")
        
        try:
            if choice == "1":
                balance = check_balance(db, username)
                print(f"balance: {balance}")
                
            elif choice == "2":
                amount = float(input("amount: "))
                withdraw(db, username, amount)
                print("done")
                
            elif choice == "3":
                amount = float(input("amount: "))
                deposit(db, username, amount)
                print("done")
                
            elif choice == "4":
                old_pin = getpass.getpass("old pin: ")
                new_pin = getpass.getpass("new pin: ")
                change_pin(db, username, old_pin, new_pin)
                print("done")
                
            elif choice == "5":
                break
            else:
                print("bad choice")
                
        except Exception as e:
            print("error:", e)

def ensure_admin(db):
    """make admin"""
    for username, info in db["users"].items():
        if info["role"] == "admin":
            return
    
    print("CREATE ADMIN")
    while True:
        username = input("username (admin): ") or "admin"
        pin = getpass.getpass("pin: ")
        pin2 = getpass.getpass("pin again: ")
        
        if pin != pin2:
            print("not same")
            continue
        
        create_user(db, username, pin, role="admin", balance=0)
        print(f"admin {username} created")
        break

def main():
    db = load_db()
    ensure_admin(db)
    
    print("ATM")
    
    while True:
        print("\n1) login")
        print("2) exit")
        
        choice = input("choice: ")
        
        if choice == "1":
            username = input("username: ")
            
            if username not in db["users"]:
                print("no user")
                continue
            
            if not authenticate(db, username):
                continue
            
            role = db["users"][username]["role"]
            
            if role == "admin":
                admin_menu(db, username)
            else:
                user_menu(db, username)
                
        elif choice == "2":
            print("bye")
            sys.exit(0)
        else:
            print("bad choice")

if __name__ == "__main__":
    main()
