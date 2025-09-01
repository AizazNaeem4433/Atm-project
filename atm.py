#!/usr/bin/env python3
# ATM-project/atm.py
"""
ATM program - upgraded version
Features:
- Admin role management
- Developer/DB control
- First-time login PIN setup
- Secure PIN handling
"""

import json
import os
import hashlib
import secrets
import getpass
import time
import sys

DB_FILE = "db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        new_db = {"atm_cash": 10000, "users": {}, "transactions": []}
        save_db(new_db)
        return new_db
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def hash_pin(pin, salt=None):
    if salt is None:
        salt = secrets.token_hex(8)
    pin_hash = hashlib.sha256((salt + pin).encode()).hexdigest()
    return salt, pin_hash

def verify_pin(pin, salt, pin_hash):
    return hashlib.sha256((salt + pin).encode()).hexdigest() == pin_hash

def log_transaction(db, username, action_type, amount, note=""):
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user": username,
        "type": action_type,
        "amount": amount,
        "note": note
    }
    db["transactions"].append(entry)
    save_db(db)

def create_user(db, username, pin=None, role="user", balance=0):
    if username in db["users"]:
        raise ValueError("user exists")
    
    salt, pin_hash = (None, None)
    if pin is not None:
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
    if username not in db["users"]:
        raise ValueError("no user")
    del db["users"][username]
    save_db(db)
    log_transaction(db, username, "delete_user", 0, "deleted")

def change_pin(db, username, old_pin, new_pin):
    user = db["users"].get(username)
    if not user:
        raise ValueError("no user")
    if user["pin_hash"] and not verify_pin(old_pin, user["pin_salt"], user["pin_hash"]):
        raise ValueError("wrong pin")
    salt, pin_hash = hash_pin(new_pin)
    user["pin_salt"] = salt
    user["pin_hash"] = pin_hash
    save_db(db)
    log_transaction(db, username, "change_pin", 0, "")

def check_balance(db, username):
    user = db["users"].get(username)
    if not user:
        raise ValueError("no user")
    return user["balance"]

def deposit(db, username, amount):
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
    if amount <= 0:
        raise ValueError("bad amount")
    user = db["users"].get(username)
    if not user:
        raise ValueError("no user")
    if user["balance"] < amount:
        raise ValueError("insufficient funds")
    if db["atm_cash"] < amount:
        raise ValueError("ATM out of cash")
    user["balance"] -= amount
    db["atm_cash"] -= amount
    save_db(db)
    log_transaction(db, username, "withdraw", amount, "")
    return True

def list_users(db):
    summary = {}
    for username, info in db["users"].items():
        summary[username] = {"role": info["role"], "balance": info["balance"]}
    return summary

def view_transactions(db, limit=20):
    return db["transactions"][-limit:]

def set_atm_cash(db, amount):
    db["atm_cash"] = float(amount)
    save_db(db)
    log_transaction(db, "admin", "set_atm_cash", amount, "")

def change_role(db, username, new_role):
    if username not in db["users"]:
        raise ValueError("no such user")
    old_role = db["users"][username]["role"]
    db["users"][username]["role"] = new_role
    save_db(db)
    log_transaction(db, "admin", "change_role", 0, f"{username}: {old_role} -> {new_role}")

def first_time_login(db, username):
    user = db["users"][username]
    if user["pin_hash"]:
        return
    print(f"Welcome {username}, please create your PIN:")
    while True:
        pin = input("Enter new PIN: ")
        pin2 = input("Confirm PIN: ")
        if pin != pin2:
            print("PINs do not match! Try again.")
            continue
        salt, pin_hash = hash_pin(pin)
        user["pin_salt"] = salt
        user["pin_hash"] = pin_hash
        save_db(db)
        log_transaction(db, username, "set_pin", 0, "first-time setup")
        print("PIN created successfully!")
        break

def authenticate(db, username):
    if username not in db["users"]:
        print("no user")
        return False
    first_time_login(db, username)
    user = db["users"][username]
    pin = input("PIN: ")
    if verify_pin(pin, user["pin_salt"], user["pin_hash"]):
        return True
    print("wrong pin")
    return False

def admin_menu(db, admin_username):
    while True:
        print("\nADMIN MENU")
        print("1) list users")
        print("2) create user")
        print("3) delete user")
        print("4) view transactions")
        print("5) set ATM cash")
        print("6) change user role")
        print("7) exit")
        choice = input("choice: ")
        try:
            if choice == "1":
                for u, info in list_users(db).items():
                    print(f"{u}: {info['role']}, {info['balance']}")
            elif choice == "2":
                username = input("username: ")
                role = input("role (user): ") or "user"
                balance = float(input("balance (0): ") or 0)
                create_user(db, username, pin=None, role=role, balance=balance)
                print("user created; they must set PIN on first login")
            elif choice == "3":
                username = input("username: ")
                confirm = input("delete? (yes): ")
                if confirm.lower() == "yes":
                    delete_user(db, username)
                    print("deleted")
            elif choice == "4":
                for tx in view_transactions(db):
                    print(tx)
            elif choice == "5":
                amount = float(input("ATM cash: "))
                set_atm_cash(db, amount)
                print("done")
            elif choice == "6":
                username = input("username: ")
                new_role = input("new role: ")
                change_role(db, username, new_role)
                print(f"{username} role updated")
            elif choice == "7":
                break
            else:
                print("bad choice")
        except Exception as e:
            print("error:", e)

def user_menu(db, username):
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
                print(f"Balance: {check_balance(db, username)}")
            elif choice == "2":
                amount = float(input("amount: "))
                withdraw(db, username, amount)
                print("done")
            elif choice == "3":
                amount = float(input("amount: "))
                deposit(db, username, amount)
                print("done")
            elif choice == "4":
                old_pin = input("old PIN: ")
                new_pin = input("new PIN: ")
                change_pin(db, username, old_pin, new_pin)
                print("done")
            elif choice == "5":
                break
            else:
                print("bad choice")
        except Exception as e:
            print("error:", e)

def ensure_admin(db):
    for u, info in db["users"].items():
        if info["role"] == "admin":
            return
    print("CREATE ADMIN")
    while True:
        username = input("username (admin): ") or "admin"
        pin = input("pin: ")
        pin2 = input("pin again: ")
        if pin != pin2:
            print("PINs do not match")
            continue
        create_user(db, username, pin, role="admin")
        print(f"Admin {username} created")
        break

def main():
    db = load_db()
    ensure_admin(db)
    print("ATM SYSTEM")
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
