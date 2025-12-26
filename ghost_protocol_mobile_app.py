# -*- coding: utf-8 -*-
# GhostProtocol Mobile Node & Server
# TR: Bu dosya GhostProtocol tam düğümünü mobil cihazlar için Kivy uygulamasına dönüştürür.
# EN: This file converts the GhostProtocol full node into a Kivy application for mobile devices.
# Includes: Smart Contracts, Treasury, Messenger, Mesh Network.

import threading
import time
import os
import webbrowser
import hashlib
import json
import sqlite3
import base64
import random
import re
import logging
import requests 
import socket
from typing import Optional, Tuple, Dict, Any, List
from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for, Response
from uuid import uuid4
from datetime import timedelta, datetime
from markupsafe import Markup 
from jinja2 import DictLoader, Template 
from werkzeug.utils import secure_filename

# Kivy Imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.utils import platform

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GhostMobile - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostMobile")

# --- YAPILANDIRMA / CONFIGURATION ---
GHOST_PORT = 5000
BASE_DIFFICULTY = 4 
TOTAL_SUPPLY = 100000000.0 
INITIAL_BLOCK_REWARD = 50.0 
HALVING_INTERVAL = 2000
DOMAIN_EXPIRY_SECONDS = 15552000
STORAGE_COST_PER_MB = 0.01
DOMAIN_REGISTRATION_FEE = 1.0
INITIAL_USER_BALANCE = 0.0 # TR: Mobil kullanıcı da madencilikle kazanmalı / EN: Mobile user should earn via mining
MESSAGE_FEE = 0.00001
INVITE_FEE = 0.00001
CONTRACT_DEPLOY_FEE = 2.0         
CONTRACT_CALL_FEE = 0.001 

# TR: Ağ gelirlerinin birikeceği Hazine Cüzdanı Adresi
# EN: Treasury Wallet Address where network revenues will accumulate
TREASURY_WALLET_KEY = "GHST_NETWORK_TREASURY_VAULT"

KNOWN_PEERS = ["46.101.219.46", "68.183.12.91"] 

# --- GHOST VM (EMBEDDED FOR MOBILE) ---
class GhostVM:
    def __init__(self):
        self.safe_builtins = {
            'abs': abs, 'dict': dict, 'int': int, 'list': list, 
            'len': len, 'str': str, 'sum': sum, 'range': range,
            'max': max, 'min': min, 'round': round, 'bool': bool,
            'float': float, 'set': set, 'tuple': tuple
        }

    def validate_code(self, code_str):
        banned = ['import', 'open', 'exec', 'eval', '__import__', 'os.', 'sys.', 'subprocess', 'input']
        for b in banned:
            if b in code_str:
                return False, f"Security Violation: '{b}' is forbidden."
        return True, "OK"

    def execute_contract(self, code, method_name, args, current_state):
        state_to_use = current_state.copy() if current_state else {}
        restricted_globals = {"__builtins__": self.safe_builtins, "state": state_to_use}
        local_scope = {}
        try:
            exec(code, restricted_globals, local_scope)
            method_to_call = local_scope.get(method_name) or restricted_globals.get(method_name)
            if method_to_call and callable(method_to_call):
                result = method_to_call(*args)
                new_state = restricted_globals.get('state', state_to_use)
                return {'success': True, 'result': result, 'new_state': new_state}
            else:
                return {'success': False, 'error': f"Method '{method_name}' not found."}
        except Exception as e:
            return {'success': False, 'error': str(e)}

EXAMPLE_CONTRACT = """
def init():
    state['counter'] = 0
    return "Initialized"

def increment(amount):
    state['counter'] = state.get('counter', 0) + int(amount)
    return state['counter']
"""

# Flask App Setup
server = Flask(__name__)
server.secret_key = 'ghost_mobile_final_v2'
server.permanent_session_lifetime = timedelta(days=7)

# --- ÇOKLU DİL SÖZLÜĞÜ / MULTI-LANGUAGE DICTIONARY ---
LANGUAGES = {
    'tr': {
        'title': "GhostProtocol Mobil", 'status_online': "ÇEVRİMİÇİ", 'status_offline': "ÇEVRİMDIŞI",
        'server_status': "Sunucu Durumu", 'active_peers': "Aktif Düğüm",
        'dashboard_title': "Panel", 'mining_title': "Madencilik", 'logout': "Çıkış", 'login': "Giriş", 'register': "Kayıt", 'search': "Arama",
        'wallet_title': "💳 Cüzdanım", 'pubkey': "Public Key (Hash)", 'balance': "Bakiye",
        'domain_title': "💾 .ghost Kayıt", 'media_title': "🖼️ Varlık Yükle", 'asset_action': "İşlem", 
        'status_success': "Başarılı", 'status_failed': "Başarısız", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Link Kopyala",
        'media_info': "Desteklenen: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Yayınla", 
        'search_title': "🔍 Ghost Arama", 'edit': "Düzenle", 'delete': "Sil",
        'login_prompt': "Giriş Yap", 'username': "Kullanıcı Adı", 'password': "Şifre", 'submit': "Gönder",
        'asset_fee': "Ücret", 'asset_expires': "Süre Sonu", 'mine_success': "Blok Başarılı", 
        'mine_message': "Yeni blok bulundu: {{ block_hash }}. Ödül: {{ reward }} GHOST.",
        'mine_limit_error': "Günlük limit dolmadı.", 'wallet_address': "Cüzdan Adresi", 'last_transactions': "Son İşlemler", 
        'tx_id': "İşlem ID", 'tx_sender': "Gönderen", 'tx_recipient': "Alıcı", 'tx_amount': "Miktar", 'tx_timestamp': "Zaman",
        'no_transactions': "İşlem yok.", 'total_supply': "Toplam Arz", 'mined_supply': "Dolaşımdaki Arz", 'remaining_supply': "Kalan Arz",
        'mine_last_block': "Son Blok", 'mine_difficulty': "Zorluk", 'mine_reward': "Ödül",
        'blocks_to_halving': "Yarılanmaya Kalan", 'view': "Görüntüle", 'back_to_dashboard': "Panele Dön",
        'send_coin_title': "Para Gönder", 'recipient_address': "Alıcı Adresi", 'amount': "Miktar", 'send_btn': "Gönder",
        'insufficient_balance': "Yetersiz bakiye.", 'transfer_success': "Başarılı.", 'recipient_not_found': "Alıcı yok.",
        'asset_name': "Varlık Adı", 'asset_type': "Tür", 'my_assets_title': "Varlıklarım", 'update_btn': "Güncelle", 'edit_title': "Düzenle",
        'content_placeholder': "İçerik", 'stats_title': "Ghost İstatistikleri", 'solved_blocks': "Çözülen Blok",
        'messenger_title': "GhostMessenger", 'msg_friends': "Arkadaşlar", 'msg_chat': "Sohbet",
        'msg_send': "Gönder", 'msg_invite': "Davet Et", 'msg_attach': "Varlık Ekle",
        'msg_placeholder': "Mesaj...",
        'contracts_title': "📜 Akıllı Kontratlar", 'contract_deploy': "Yeni Kontrat Yükle", 'contract_interact': "Kontrat ile Etkileş",
        'contract_code': "Python Kodu", 'contract_address': "Kontrat Adresi", 'method_name': "Metot Adı", 'method_args': "Argümanlar (virgülle ayır)",
        'deploy_btn': "Yükle (2 GHOST)", 'call_btn': "Çalıştır (0.001 GHOST)", 'contract_result': "Sonuç", 
        'contract_desc': "Akıllı kontratları dağıtın ve etkileşime geçin.", 'my_contracts': "Kontratlarım",
        'contract_date': "Tarih", 'no_contracts': "Henüz kontrat yok."
    },
    'en': {
        'title': "GhostProtocol Mobile", 'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'server_status': "Server Status", 'active_peers': "Active Peers",
        'dashboard_title': "Dashboard", 'mining_title': "Mining", 'logout': "Logout", 'login': "Login", 'register': "Register", 'search': "Search",
        'wallet_title': "💳 My Wallet", 'pubkey': "Public Key", 'balance': "Balance",
        'domain_title': "💾 .ghost Reg", 'media_title': "🖼️ Upload", 'asset_action': "Action", 
        'status_success': "Success", 'status_failed': "Failed", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Copy Link",
        'media_info': "Supported: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Publish", 
        'search_title': "🔍 Search", 'edit': "Edit", 'delete': "Delete",
        'login_prompt': "Login", 'username': "Username", 'password': "Password", 'submit': "Submit",
        'asset_fee': "Fee", 'asset_expires': "Expires", 'mine_success': "Block Mined", 
        'mine_message': "Block found: {{ block_hash }}. Reward: {{ reward }} GHOST.",
        'mine_limit_error': "Daily limit not reached.", 'wallet_address': "Address", 'last_transactions': "Transactions", 
        'tx_id': "Tx ID", 'tx_sender': "Sender", 'tx_recipient': "Recipient", 'tx_amount': "Amount", 'tx_timestamp': "Time",
        'no_transactions': "No transactions.", 'total_supply': "Total Supply", 'mined_supply': "Circulating", 'remaining_supply': "Remaining",
        'mine_last_block': "Last Block", 'mine_difficulty': "Difficulty", 'mine_reward': "Reward",
        'blocks_to_halving': "Halving in", 'view': "View", 'back_to_dashboard': "Back",
        'send_coin_title': "Send Coin", 'recipient_address': "Recipient", 'amount': "Amount", 'send_btn': "Send",
        'insufficient_balance': "Low balance.", 'transfer_success': "Success.", 'recipient_not_found': "Not found.",
        'asset_name': "Asset Name", 'asset_type': "Type", 'my_assets_title': "My Assets", 'update_btn': "Update", 'edit_title': "Edit",
        'content_placeholder': "Content", 'stats_title': "Stats", 'solved_blocks': "Solved Blocks",
        'messenger_title': "GhostMessenger", 'msg_friends': "Friends", 'msg_chat': "Chat",
        'msg_send': "Send", 'msg_invite': "Invite", 'msg_attach': "Attach",
        'msg_placeholder': "Message...",
        'contracts_title': "📜 Smart Contracts", 'contract_deploy': "Deploy New Contract", 'contract_interact': "Interact with Contract",
        'contract_code': "Python Code", 'contract_address': "Contract Address", 'method_name': "Method Name", 'method_args': "Arguments (comma separated)",
        'deploy_btn': "Deploy (2 GHOST)", 'call_btn': "Execute (0.001 GHOST)", 'contract_result': "Result", 
        'contract_desc': "Deploy and interact with smart contracts.", 'my_contracts': "My Contracts",
        'contract_date': "Date", 'no_contracts': "No contracts found."
    },
     'ru': {
        'title': "Сервер GhostProtocol", 'status_online': "ОНЛАЙН", 'status_offline': "ОФФЛАЙН",
        'server_status': "Статус", 'active_peers': "Пиры",
        'dashboard_title': "Панель", 'mining_title': "Майнинг", 'logout': "Выход", 'login': "Вход", 'register': "Регистрация", 'search': "Поиск",
        'wallet_title': "💳 Кошелек", 'pubkey': "Ключ", 'balance': "Баланс",
        'domain_title': "💾 .ghost", 'media_title': "🖼️ Загрузить", 'asset_action': "Действие", 
        'status_success': "Успех", 'status_failed': "Ошибка", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Копия",
        'media_info': "Поддержка: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Опубликовать", 
        'search_title': "🔍 Поиск", 'edit': "Правка", 'delete': "Удалить",
        'login_prompt': "Вход", 'username': "Имя", 'password': "Пароль", 'submit': "Отправить",
        'asset_fee': "Плата", 'asset_expires': "Срок", 'mine_success': "Блок найден", 
        'mine_message': "Блок: {{ block_hash }}. Награда: {{ reward }} GHOST.",
        'mine_limit_error': "Лимит не истек.", 'wallet_address': "Адрес", 'last_transactions': "Транзакции", 
        'tx_id': "ID", 'tx_sender': "Отпр.", 'tx_recipient': "Получ.", 'tx_amount': "Сумма", 'tx_timestamp': "Время",
        'no_transactions': "Нет данных.", 'total_supply': "Всего", 'mined_supply': "В обороте", 'remaining_supply': "Остаток",
        'mine_last_block': "Посл. блок", 'mine_difficulty': "Сложность", 'mine_reward': "Награда",
        'blocks_to_halving': "До халвинга", 'view': "Вид", 'back_to_dashboard': "Назад",
        'send_coin_title': "Перевод", 'recipient_address': "Получатель", 'amount': "Сумма", 'send_btn': "Отправить",
        'insufficient_balance': "Мало средств.", 'transfer_success': "Успешно.", 'recipient_not_found': "Не найден.",
        'asset_name': "Имя", 'asset_type': "Тип", 'my_assets_title': "Активы", 'update_btn': "Обновить", 'edit_title': "Правка",
        'content_placeholder': "Контент", 'stats_title': "Статистика", 'solved_blocks': "Блоки",
        'messenger_title': "GhostMessenger", 'msg_friends': "Друзья", 'msg_chat': "Чат",
        'msg_send': "Отпр.", 'msg_invite': "Пригласить", 'msg_attach': "Прикрепить",
        'msg_placeholder': "Сообщение...",
        'contracts_title': "📜 Смарт-контракты", 'contract_deploy': "Развернуть", 'contract_interact': "Взаимодействие",
        'contract_code': "Код Python", 'contract_address': "Адрес контракта", 'method_name': "Имя метода", 'method_args': "Аргументы",
        'deploy_btn': "Развернуть (2 GHOST)", 'call_btn': "Выполнить (0.001 GHOST)", 'contract_result': "Результат", 
        'contract_desc': "Развертывание и взаимодействие со смарт-контрактами.", 'my_contracts': "Мои контракты",
        'contract_date': "Дата", 'no_contracts': "Контракты не найдены."
    },
    'hy': {
        'title': "GhostProtocol Սերվեր", 'status_online': "ԱՌՑԱՆՑ", 'status_offline': "ԱՆՑԱՆՑ",
        'server_status': "Կարգավիճակ", 'active_peers': "Ակտիվ",
        'dashboard_title': "Վահանակ", 'mining_title': "Մայնինգ", 'logout': "Ելք", 'login': "Մուտք", 'register': "Գրանցվել", 'search': "Որոնում",
        'wallet_title': "💳 Իմ Դրամապանակը", 'pubkey': "Բանալի", 'balance': "Հաշվեկշիռ",
        'domain_title': "💾 .ghost Գրանցում", 'media_title': "🖼️ Բեռնել Ակտիվ", 'asset_action': "Գործողություն", 
        'status_success': "Հաջող", 'status_failed': "Ձախողում", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Պատճենել",
        'media_info': "Աջակցվում է՝ .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Հրապարակել", 
        'search_title': "🔍 Որոնում", 'edit': "Խմբ.", 'delete': "Ջնջել",
        'login_prompt': "Մուտք", 'username': "Անուն", 'password': "Գաղտնաբառ", 'submit': "Ուղարկել",
        'asset_fee': "Վճար", 'asset_expires': "Ժամկետ", 'mine_success': "Բլոկ", 
        'mine_message': "Բլոկ: {{ block_hash }}. Պարգև: {{ reward }} GHOST.",
        'mine_limit_error': "Սահմանաչափ:", 'wallet_address': "Հասցե", 'last_transactions': "Գործարքներ", 
        'tx_id': "ID", 'tx_sender': "Ուղարկող", 'tx_recipient': "Ստացող", 'tx_amount': "Գումար", 'tx_timestamp': "Ժամանակ",
        'no_transactions': "Չկան:", 'total_supply': "Ընդհանուր", 'mined_supply': "Շրջանառվող", 'remaining_supply': "Մնացորդ",
        'mine_last_block': "Վերջին բլոկ", 'mine_difficulty': "Բարդություն", 'mine_reward': "Պարգև",
        'blocks_to_halving': "Մինչ կիսում", 'view': "Դիտել", 'back_to_dashboard': "Վերադառնալ",
        'send_coin_title': "Ուղարկել", 'recipient_address': "Ստացող", 'amount': "Գումար", 'send_btn': "Ուղարկել",
        'insufficient_balance': "Քիչ գումար:", 'transfer_success': "Հաջող:", 'recipient_not_found': "Չգտնվեց:",
        'asset_name': "Անուն", 'asset_type': "Տեսակ", 'my_assets_title': "Ակտիվներ", 'update_btn': "Թարմացնել", 'edit_title': "Խմբ.",
        'content_placeholder': "Բովանդակություն", 'stats_title': "Վիճակագրություն", 'solved_blocks': "Լուծված",
        'messenger_title': "GhostMessenger", 'msg_friends': "Ընկերներ", 'msg_chat': "Զրույց",
        'msg_send': "Ուղարկել", 'msg_invite': "Հրավիրել", 'msg_attach': "Կցել",
        'msg_placeholder': "Նամակ...",
        'contracts_title': "📜 Խելացի պայմանագրեր", 'contract_deploy': "Տեղադրել", 'contract_interact': "Փոխազդեցություն",
        'contract_code': "Python Կոդ", 'contract_address': "Հասցե", 'method_name': "Մեթոդ", 'method_args': "Արգումենտներ",
        'deploy_btn': "Տեղադրել (2 GHOST)", 'call_btn': "Կատարել (0.001 GHOST)", 'contract_result': "Արդյունք", 
        'contract_desc': "Տեղադրել և օգտագործել խելացի պայմանագրեր:", 'my_contracts': "Իմ պայմանագրերը",
        'contract_date': "Ամսաթիվ", 'no_contracts': "Պայմանագրեր չեն գտնվել:"
    }
}

# --- GLOBAL VARIABLES FOR DB (KIVY HOOK) ---
db_file_path = ""

# --- YARDIMCI FONKSİYONLAR / HELPER FUNCTIONS ---
def generate_user_keys(username):
    original_hash = hashlib.sha256(username.encode()).hexdigest()[:20]
    ghst_address = f"GHST{original_hash}" 
    return original_hash, ghst_address

def generate_qr_code_link(ghst_address):
    return f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={ghst_address}"

def extract_keywords(content_str):
    try:
        text = re.sub(r'<(script|style).*?>.*?</\1>', '', content_str, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<.*?>', ' ', text)
        text = re.sub(r'[^a-zA-ZğüşıöçĞÜŞİÖÇ ]', ' ', text)
        return ",".join(list(set([w for w in text.lower().split() if len(w) > 2]))[:20])
    except: return ""

def calculate_asset_fee(size_bytes, asset_type):
    if asset_type == 'domain': return DOMAIN_REGISTRATION_FEE
    return round((size_bytes / (1024 * 1024)) * STORAGE_COST_PER_MB, 5)

def calculate_difficulty(active_peer_count):
    increase = active_peer_count // 5
    return BASE_DIFFICULTY + increase

# --- VERİTABANI YÖNETİCİSİ / DATABASE MANAGER ---
class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=20) 
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 0, last_mined REAL DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, previous_hash TEXT, block_hash TEXT, proof INTEGER, miner_key TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS friends (user_key TEXT, friend_key TEXT, status TEXT, PRIMARY KEY(user_key, friend_key))''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (msg_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, content TEXT, asset_id TEXT, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS network_fees (fee_type TEXT PRIMARY KEY, amount REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS contracts (contract_address TEXT PRIMARY KEY, owner_key TEXT, code TEXT, state TEXT, creation_time REAL)''')
        
        default_fees = [
            ('domain_reg', DOMAIN_REGISTRATION_FEE), ('storage_mb', STORAGE_COST_PER_MB), 
            ('msg_fee', MESSAGE_FEE), ('invite_fee', INVITE_FEE),
            ('contract_deploy', CONTRACT_DEPLOY_FEE), ('contract_call', CONTRACT_CALL_FEE)
        ]
        for key, val in default_fees:
            c.execute("INSERT OR IGNORE INTO network_fees (fee_type, amount) VALUES (?, ?)", (key, val))

        try: c.execute("SELECT last_mined FROM users LIMIT 1")
        except sqlite3.OperationalError: c.execute("ALTER TABLE users ADD COLUMN last_mined REAL DEFAULT 0")

        if c.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
            genesis_hash = hashlib.sha256(b'GhostGenesis').hexdigest()
            c.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                       (1, time.time(), '0', genesis_hash, 100, 'GhostProtocol_System'))
        
        # TR: Sistem Hazine Cüzdanını oluştur
        # EN: Create System Treasury Wallet
        if c.execute("SELECT COUNT(*) FROM users WHERE wallet_public_key = ?", (TREASURY_WALLET_KEY,)).fetchone()[0] == 0:
            c.execute("INSERT INTO users (username, password, wallet_public_key, balance) VALUES (?, ?, ?, ?)",
                      ('Network_Treasury', 'sys_locked_v1', TREASURY_WALLET_KEY, 0.0))

        conn.commit()
        conn.close()

    def get_fee(self, fee_type):
        conn = self.get_connection()
        res = conn.execute("SELECT amount FROM network_fees WHERE fee_type = ?", (fee_type,)).fetchone()
        conn.close()
        return float(res['amount']) if res else 0.0

# --- MANAGER CLASSES ---

class SmartContractManager:
    def __init__(self, db_mgr, blockchain_mgr, vm):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.vm = vm

    def deploy_contract(self, owner_key, code):
        fee = self.db.get_fee('contract_deploy')
        conn = self.db.get_connection()
        try:
            user = conn.execute("SELECT balance FROM users WHERE wallet_public_key=?",(owner_key,)).fetchone()
            if not user or float(user['balance']) < fee: return False, f"Low Balance ({fee} GHOST)"

            valid, msg = self.vm.validate_code(code)
            if not valid: return False, msg

            contract_address = "CNT" + hashlib.sha256(str(uuid4()).encode()).hexdigest()[:20]
            timestamp = time.time()
            init_res = self.vm.execute_contract(code, "init", [], {})
            state = init_res.get('new_state', {})
            state_json = json.dumps(state)

            conn.execute("INSERT INTO contracts (contract_address, owner_key, code, state, creation_time) VALUES (?,?,?,?,?)",
                         (contract_address, owner_key, code, state_json, timestamp))
            
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (fee, owner_key))
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (fee, TREASURY_WALLET_KEY))
            
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (str(uuid4()), owner_key, TREASURY_WALLET_KEY, fee, timestamp))
            conn.commit()
            return True, contract_address
        except Exception as e: return False, str(e)
        finally: conn.close()

    def call_contract(self, sender_key, contract_address, method, args):
        fee = self.db.get_fee('contract_call')
        conn = self.db.get_connection()
        try:
            contract = conn.execute("SELECT * FROM contracts WHERE contract_address=?",(contract_address,)).fetchone()
            if not contract: return False, "Contract not found."
            
            user = conn.execute("SELECT balance FROM users WHERE wallet_public_key=?", (sender_key,)).fetchone()
            if not user or float(user['balance']) < fee: return False, f"Low Balance ({fee} GHOST)"

            current_state = json.loads(contract['state'])
            args_list = [x.strip() for x in args.split(',') if x.strip()]
            clean_args = []
            for a in args_list:
                try: clean_args.append(int(a))
                except: clean_args.append(a)

            result = self.vm.execute_contract(contract['code'], method, clean_args, current_state)
            
            if result['success']:
                new_state_json = json.dumps(result['new_state'])
                conn.execute("UPDATE contracts SET state = ? WHERE contract_address = ?", (new_state_json, contract_address))
                conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (fee, sender_key))
                conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (fee, TREASURY_WALLET_KEY))
                conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                             (str(uuid4()), sender_key, TREASURY_WALLET_KEY, fee, time.time()))
                conn.commit()
                return True, str(result['result'])
            else: return False, result['error']
        except Exception as e: return False, str(e)
        finally: conn.close()

    def get_user_contracts(self, user_key):
        conn = self.db.get_connection()
        res = conn.execute("SELECT contract_address, creation_time FROM contracts WHERE owner_key=?",(user_key,)).fetchall()
        conn.close()
        return [dict(x) for x in res]

class MessengerManager:
    def __init__(self, db_mgr, blockchain_mgr, mesh_mgr):
        self.db = db_mgr
        self.chain_mgr = blockchain_mgr
        self.mesh_mgr = mesh_mgr

    def send_invite(self, sender_key, friend_username):
        fee = self.db.get_fee('invite_fee')
        conn = self.db.get_connection()
        try:
            sender = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender_key,)).fetchone()
            if not sender or float(sender['balance']) < fee:
                return False, f"Low Balance ({fee} GHOST)"

            friend = conn.execute("SELECT wallet_public_key FROM users WHERE username = ?", (friend_username,)).fetchone()
            if not friend: return False, "User not found."
            friend_key = friend['wallet_public_key']
            
            conn.execute("INSERT OR REPLACE INTO friends (user_key, friend_key, status) VALUES (?, ?, ?)", (sender_key, friend_key, 'accepted'))
            conn.execute("INSERT OR REPLACE INTO friends (user_key, friend_key, status) VALUES (?, ?, ?)", (friend_key, sender_key, 'accepted'))
            
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (fee, sender_key))
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (fee, TREASURY_WALLET_KEY))
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (str(uuid4()), sender_key, TREASURY_WALLET_KEY, fee, time.time()))
            conn.commit()
            return True, "Friend Added."
        finally: conn.close()

    def send_message(self, sender_key, recipient_key, content, asset_id=None):
        fee = self.db.get_fee('msg_fee')
        conn = self.db.get_connection()
        try:
            sender = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender_key,)).fetchone()
            if not sender or float(sender['balance']) < fee:
                return False, f"Low Balance ({fee} GHOST)"

            msg_id = str(uuid4())
            timestamp = time.time()
            encrypted_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

            conn.execute("INSERT INTO messages (msg_id, sender, recipient, content, asset_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                         (msg_id, sender_key, recipient_key, encrypted_content, asset_id, timestamp))
            
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (fee, sender_key))
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (fee, TREASURY_WALLET_KEY))
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (str(uuid4()), sender_key, TREASURY_WALLET_KEY, fee, timestamp))
            conn.commit()
            
            msg_data = {'type': 'message', 'msg_id': msg_id, 'sender': sender_key, 'recipient': recipient_key, 'content': encrypted_content, 'asset_id': asset_id, 'timestamp': timestamp}
            if self.mesh_mgr: self.mesh_mgr.broadcast_message(msg_data)
            return True, "Message Sent."
        finally: conn.close()

    def receive_message(self, msg_data):
        conn = self.db.get_connection()
        try:
            exists = conn.execute("SELECT msg_id FROM messages WHERE msg_id = ?", (msg_data['msg_id'],)).fetchone()
            if not exists:
                conn.execute("INSERT INTO messages (msg_id, sender, recipient, content, asset_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                             (msg_data['msg_id'], msg_data['sender'], msg_data['recipient'], msg_data['content'], msg_data['asset_id'], msg_data['timestamp']))
                conn.commit()
        except: pass
        finally: conn.close()

    def get_messages(self, user_key, friend_key):
        conn = self.db.get_connection()
        msgs = conn.execute("SELECT * FROM messages WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?) ORDER BY timestamp ASC",
                            (user_key, friend_key, friend_key, user_key)).fetchall()
        conn.close()
        decoded = []
        for m in msgs:
            d = dict(m)
            try: d['content'] = base64.b64decode(d['content']).decode('utf-8')
            except: d['content'] = "[Encrypted]"
            decoded.append(d)
        return decoded

    def get_friends(self, user_key):
        conn = self.db.get_connection()
        friends = conn.execute("SELECT f.friend_key, u.username FROM friends f JOIN users u ON f.friend_key = u.wallet_public_key WHERE f.user_key = ?", (user_key,)).fetchall()
        conn.close()
        return [dict(f) for f in friends]

class AssetManager:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def register_asset(self, owner_key, asset_type, name, content, is_file=False):
        if asset_type == 'domain' and not name.endswith('.ghost'): name += '.ghost'
        if not content and asset_type == 'domain': content = "<h1>New Ghost Site</h1>"

        if is_file:
            content.seek(0)
            content_bytes = content.read()
        else:
            content_bytes = content.encode('utf-8')
            keywords = extract_keywords(content) if asset_type == 'domain' else ""
            
        size = len(content_bytes)
        fee = self.db.get_fee('domain_reg') if asset_type == 'domain' else (size / (1024*1024)) * self.db.get_fee('storage_mb')

        conn = self.db.get_connection()
        user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (owner_key,)).fetchone()
        
        if not user or float(user['balance']) < fee: 
             conn.close()
             return False, f"Low Balance ({fee} GHOST)"

        try:
            conn.execute("INSERT OR REPLACE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (str(uuid4()), owner_key, asset_type, name, content_bytes, size, time.time(), time.time() + DOMAIN_EXPIRY_SECONDS, keywords))
            
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (fee, owner_key))
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (fee, TREASURY_WALLET_KEY))
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (str(uuid4()), owner_key, TREASURY_WALLET_KEY, fee, time.time()))
            conn.commit()
            return True, "Success"
        except Exception as e: return False, str(e)
        finally: conn.close()

    def update_asset_content(self, asset_id, owner_key, new_content):
        conn = self.db.get_connection()
        try:
            keywords = extract_keywords(new_content)
            content_bytes = new_content.encode('utf-8')
            conn.execute("UPDATE assets SET content = ?, keywords = ? WHERE asset_id = ? AND owner_pub_key = ?", 
                         (content_bytes, keywords, asset_id, owner_key))
            conn.commit()
            return True, "Updated."
        except Exception as e: return False, str(e)
        finally: conn.close()

    def delete_asset(self, asset_id, owner_key):
        conn = self.db.get_connection()
        try:
            conn.execute("DELETE FROM assets WHERE asset_id = ? AND owner_pub_key = ?", (asset_id, owner_key))
            conn.commit()
            return True, "Deleted."
        except Exception as e: return False, str(e)
        finally: conn.close()

    def get_all_assets_meta(self):
        conn = self.db.get_connection()
        assets = conn.execute("SELECT asset_id, owner_pub_key, type, name, creation_time FROM assets").fetchall()
        conn.close()
        return [dict(a) for a in assets]

    def get_asset_by_id(self, asset_id):
        conn = self.db.get_connection()
        asset = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
        conn.close()
        if asset:
            d = dict(asset)
            d['content'] = base64.b64encode(d['content']).decode('utf-8')
            return d
        return None

    def sync_asset(self, asset_data):
        conn = self.db.get_connection()
        try:
            content_bytes = base64.b64decode(asset_data['content'])
            conn.execute("INSERT OR IGNORE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_data['asset_id'], asset_data['owner_pub_key'], asset_data['type'], asset_data['name'], content_bytes, 
                          len(content_bytes), asset_data['creation_time'], asset_data['expiry_time'], asset_data.get('keywords', '')))
            conn.commit()
        except: pass
        finally: conn.close()

class BlockchainManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.mesh_mgr = None 

    def set_mesh_manager(self, mgr):
        self.mesh_mgr = mgr

    def get_last_block(self):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return dict(block)

    def get_statistics(self):
        conn = self.db.get_connection()
        mined_supply = conn.execute("SELECT SUM(amount) FROM transactions WHERE sender = 'GhostProtocol_System'").fetchone()[0] or 0.0
        last_block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        current_block_index = last_block['block_index']
        halvings = current_block_index // HALVING_INTERVAL
        current_reward = INITIAL_BLOCK_REWARD / (2**halvings)
        remaining_blocks = HALVING_INTERVAL - (current_block_index % HALVING_INTERVAL)
        conn.close()
        return {
            'total_supply': TOTAL_SUPPLY,
            'circulating_supply': mined_supply,
            'remaining_supply': TOTAL_SUPPLY - mined_supply,
            'block_reward': current_reward,
            'solved_blocks': current_block_index,
            'blocks_until_halving': remaining_blocks
        }

    def get_all_headers(self):
        conn = self.db.get_connection()
        headers = conn.execute("SELECT block_index, block_hash FROM blocks ORDER BY block_index ASC").fetchall()
        conn.close()
        return [dict(h) for h in headers]

    def get_block_by_hash(self, block_hash):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks WHERE block_hash = ?", (block_hash,)).fetchone()
        conn.close()
        return dict(block) if block else None

    def add_block_from_peer(self, block_data):
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("INSERT OR IGNORE INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?,?,?,?,?,?)",
                         (block_data['block_index'], block_data['timestamp'], block_data['previous_hash'], block_data['block_hash'], block_data['proof'], block_data['miner_key']))
            if cursor.rowcount > 0:
                index = block_data['block_index']
                pending_txs = conn.execute("SELECT tx_id, sender, recipient, amount FROM transactions WHERE block_index = 0 OR block_index IS NULL").fetchall()
                for p_tx in pending_txs:
                    conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (p_tx['amount'], p_tx['recipient']))
                    conn.execute("UPDATE transactions SET block_index = ? WHERE tx_id = ?", (index, p_tx['tx_id']))

                reward = self.calculate_block_reward(index)
                tx_id_reward = str(uuid4()) 
                conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp, block_index) VALUES (?, ?, ?, ?, ?, ?)",
                             (tx_id_reward, "GhostProtocol_System", block_data['miner_key'], reward, block_data['timestamp'], index))
                conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (reward, block_data['miner_key']))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    def calculate_block_reward(self, current_block_index):
        halvings = current_block_index // HALVING_INTERVAL
        return INITIAL_BLOCK_REWARD / (2**halvings)

    def hash_block(self, index, timestamp, previous_hash, proof, miner_key):
        block_string = json.dumps({'index': index, 'timestamp': timestamp, 'previous_hash': previous_hash, 'proof': proof, 'miner': miner_key}, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def proof_of_work(self, last_proof, difficulty):
        proof = 0
        while True:
            guess = f'{last_proof}{proof}'.encode()
            if hashlib.sha256(guess).hexdigest()[:difficulty] == '0' * difficulty: return proof
            proof += 1

    def mine_block(self, miner_key):
        conn = self.db.get_connection()
        last_mined = conn.execute("SELECT last_mined FROM users WHERE wallet_public_key = ?", (miner_key,)).fetchone()
        if last_mined and (time.time() - last_mined['last_mined'] < 86400):
            conn.close()
            return None 

        last_block = self.get_last_block()
        index = last_block['block_index'] + 1
        active_peers_count = 0 # Simplified for mobile
        difficulty = calculate_difficulty(active_peers_count)
        proof = self.proof_of_work(last_block['proof'], difficulty)
        block_hash = self.hash_block(index, time.time(), last_block['block_hash'], proof, miner_key)
        reward = self.calculate_block_reward(index)

        try:
            conn.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                         (index, time.time(), last_block['block_hash'], block_hash, proof, miner_key))
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp, block_index) VALUES (?, ?, ?, ?, ?, ?)",
                         (str(uuid4()), "GhostProtocol_System", miner_key, reward, time.time(), index))
            conn.execute("UPDATE users SET balance = balance + ?, last_mined = ? WHERE wallet_public_key = ?", (reward, time.time(), miner_key))
            
            pending_txs = conn.execute("SELECT tx_id, sender, recipient, amount FROM transactions WHERE block_index = 0 OR block_index IS NULL").fetchall()
            for p_tx in pending_txs:
                conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (p_tx['amount'], p_tx['recipient']))
                conn.execute("UPDATE transactions SET block_index = ? WHERE tx_id = ?", (index, p_tx['tx_id']))

            conn.commit()
            return True
        except: return None 
        finally: conn.close()

    def transfer_coin(self, sender_key, recipient_key, amount):
        if sender_key == recipient_key: return False, "Kendinize gönderemezsiniz."
        amount = float(amount)
        if amount <= 0: return False, "Miktar 0'dan büyük olmalı."

        conn = self.db.get_connection()
        try:
            sender = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (sender_key,)).fetchone()
            if not sender or float(sender['balance']) < amount: return False, "Yetersiz bakiye."
            
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (amount, sender_key))
            conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (amount, recipient_key))
            
            tx_id = str(uuid4())
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp, block_index) VALUES (?, ?, ?, ?, ?, ?)",
                         (tx_id, sender_key, recipient_key, amount, time.time(), 0))
            conn.commit()
            self.broadcast_transaction({'tx_id': tx_id, 'sender': sender_key, 'recipient': recipient_key, 'amount': amount, 'timestamp': time.time()})
            return True, "Transfer başarılı."
        except Exception as e: return False, str(e)
        finally: conn.close()

    def broadcast_transaction(self, tx_data):
        def _send():
            if self.mesh_mgr:
                peers = self.mesh_mgr.get_peer_ips()
                for peer in peers:
                    try: requests.post(f"http://{peer}:{GHOST_PORT}/api/send_transaction", json=tx_data, timeout=2)
                    except: pass
        threading.Thread(target=_send, daemon=True).start()

    def receive_transaction(self, tx_data):
        conn = self.db.get_connection()
        try:
            if not conn.execute("SELECT tx_id FROM transactions WHERE tx_id = ?", (tx_data['tx_id'],)).fetchone():
                conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp, block_index) VALUES (?, ?, ?, ?, ?, ?)",
                             (tx_data['tx_id'], tx_data['sender'], tx_data['recipient'], tx_data['amount'], tx_data['timestamp'], 0))
                conn.commit()
        except: pass
        finally: conn.close()

class MeshManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except: pass
        threading.Thread(target=self._broadcast, daemon=True).start()

    def _broadcast(self):
        while True:
            try:
                # Simplified discovery for mobile
                pass
            except: pass
            time.sleep(30)

    def broadcast_message(self, msg_data):
        def _send():
            peers = self.get_peer_ips()
            for peer in peers:
                try: requests.post(f"http://{peer}:{GHOST_PORT}/api/messenger/receive_message", json=msg_data, timeout=2)
                except: pass
        threading.Thread(target=_send, daemon=True).start()

    def get_active_peers(self): return 0
    def get_peer_ips(self): return KNOWN_PEERS

class TransactionManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_last_transactions(self, pub_key, limit=10):
        conn = self.db.get_connection()
        transactions = conn.execute(
            "SELECT * FROM transactions WHERE sender = ? OR recipient = ? ORDER BY timestamp DESC LIMIT ?", 
            (pub_key, pub_key, limit)
        ).fetchall()
        conn.close()
        return transactions

# --- HTML TEMPLATES ---
# (Using the updated templates from server code)
# Using existing server templates logic but ensuring they are properly assigned.
# For mobile, we stick to the ones defined previously but update DASHBOARD_UI for contracts.

# Re-defining DASHBOARD_UI to include Smart Contract & Messenger FAB
DASHBOARD_UI = r"""{% extends 'base.html' %}{% block content %}<style>.messenger-fab { position: fixed; bottom: 20px; right: 20px; background: #00c853; color: white; padding: 15px; border-radius: 50%; cursor: pointer; box-shadow: 0 4px 8px rgba(0,0,0,0.3); font-size: 24px; z-index: 999; }.messenger-window { display: none; position: fixed; bottom: 80px; right: 20px; width: 350px; height: 500px; background: #2a2a2a; border-radius: 10px; border: 1px solid #444; box-shadow: 0 4px 12px rgba(0,0,0,0.5); flex-direction: column; z-index: 1000; }.msg-header { background: #333; padding: 10px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #444; }.msg-body { flex: 1; padding: 10px; overflow-y: auto; background: #1e1e1e; }.msg-footer { padding: 10px; background: #333; display: flex; gap: 5px; border-top: 1px solid #444; }.msg-bubble { background: #444; padding: 8px; border-radius: 8px; margin-bottom: 5px; max-width: 80%; word-wrap: break-word; }.msg-bubble.sent { background: #005c27; align-self: flex-end; margin-left: auto; }.friend-item { padding: 10px; border-bottom: 1px solid #444; cursor: pointer; display: flex; align-items: center; }.friend-item:hover { background: #333; }</style><div class="card"><h3>{{ lang['wallet_title'] }}</h3>{% if message %}<div class="status-message status-success">{{ message }}</div>{% endif %}{% if error %}<div class="status-message status-error">{{ error }}</div>{% endif %}<p><strong>{{ lang['wallet_address'] }}:</strong> {{ user_ghst_address }} <img src="{{ qr_code_link }}" style="vertical-align: middle; margin-left: 10px; width: 75px; height: 75px;"></p><p><strong>{{ lang['pubkey'] }}:</strong> {{ user_pub_key_hash }}</p><p><strong>{{ lang['balance'] }}:</strong> <span style="font-size: 1.5em; color: #ffeb3b;">{{ session.get('balance', 0) | round(4) | thousands }} GHOST</span></p><hr style="border-color:#444; margin: 15px 0;"><h4>{{ lang['send_coin_title'] }}</h4><form method="POST" action="{{ url_for('dashboard') }}" style="display:flex; gap:10px;"><input type="hidden" name="action" value="send_coin"><input type="text" name="recipient" placeholder="{{ lang['recipient_address'] }}" required style="flex:2;"><input type="number" name="amount" step="0.0001" placeholder="{{ lang['amount'] }}" required style="flex:1;"><button class="action-button" type="submit">{{ lang['send_btn'] }}</button></form></div><div style="display: flex; gap: 12px;"><div class="card" style="flex: 1;"><h3>{{ lang['domain_title'] }}</h3><p><strong>{{ lang['asset_fee'] }}:</strong> {{ DOMAIN_REGISTRATION_FEE }} GHOST</p><p><strong>Süre:</strong> 6 Ay</p><form method="POST" action="{{ url_for('dashboard') }}"><input type="hidden" name="action" value="register_domain"><input type="text" name="domain_name" placeholder="Domain Adı (ornek)" required pattern="[a-zA-Z0-9.-]+"><br><textarea name="content" placeholder="{{ lang['content_placeholder'] }}" rows="3"></textarea><br><button class="action-button" type="submit">{{ lang['register_btn'] }}</button></form></div><div class="card" style="flex: 1;"><h3>{{ lang['media_title'] }}</h3><p>{{ lang['media_info'] }}</p><form method="POST" action="{{ url_for('dashboard') }}" enctype="multipart/form-data"><input type="hidden" name="action" value="upload_media"><input type="file" name="file" required><br><button class="action-button" type="submit">{{ lang['register_btn'] }}</button></form></div></div><div class="card"><h3>{{ lang['contracts_title'] }}</h3><p>{{ lang['contract_desc'] }}</p><div style="margin-bottom:10px;"><button onclick="toggleContractSection('deploy')" class="action-button" style="width:auto;">{{ lang['contract_deploy'] }}</button> <button onclick="toggleContractSection('interact')" class="action-button" style="width:auto; background-color:#2196F3;">{{ lang['contract_interact'] }}</button></div><div id="contractDeploy" style="display:none; background:#333; padding:10px; border-radius:5px;"><h4>{{ lang['contract_deploy'] }}</h4><form method="POST"><input type="hidden" name="action" value="deploy_contract"><textarea name="code" rows="10" placeholder="{{ lang['contract_code'] }}">{{ example_contract }}</textarea><br><button class="action-button" type="submit">{{ lang['deploy_btn'] }}</button></form></div><div id="contractInteract" style="display:none; background:#333; padding:10px; border-radius:5px;"><h4>{{ lang['contract_interact'] }}</h4><form method="POST"><input type="hidden" name="action" value="call_contract"><input type="text" name="contract_address" placeholder="{{ lang['contract_address'] }}"><input type="text" name="method" placeholder="{{ lang['method_name'] }}"><input type="text" name="args" placeholder="{{ lang['method_args'] }}"><button class="action-button" type="submit">{{ lang['call_btn'] }}</button></form></div>{% if contract_result %}<div class="status-message status-success">{{ lang['contract_result'] }}: {{ contract_result }}</div>{% endif %}<h4>{{ lang['my_contracts'] }}</h4><table><tr><th>{{ lang['contract_address'] }}</th><th>{{ lang['contract_date'] }}</th></tr>{% for c in my_contracts %}<tr><td>{{ c.contract_address }}</td><td>{{ datetime.fromtimestamp(c.creation_time).strftime('%Y-%m-%d') }}</td></tr>{% else %}<tr><td colspan="2">{{ lang['no_contracts'] }}</td></tr>{% endfor %}</table></div><div class="card"><h3>{{ lang['my_assets_title'] }} ({{ assets|length }})</h3><table style="width:100%"><tr><th>{{ lang['asset_name'] }}</th> <th>{{ lang['asset_type'] }}</th> <th>{{ lang['asset_fee'] }}</th> <th>{{ lang['asset_expires'] }}</th> <th>{{ lang['asset_action'] }}</th></tr>{% for a in assets %}{% set asset_fee_calculated = calculate_asset_fee(a.storage_size, a.type)|round(4) %}{% set asset_relative_link = url_for('view_asset', asset_id=a.asset_id) %}{% set asset_external_link = url_for('view_asset', asset_id=a.asset_id, _external=True) %}<tr><td>{{ a.name }}</td><td>{{ a.type | upper }}</td><td>{{ asset_fee_calculated }} {{ lang['monthly_fee_unit'] }}</td><td>{{ datetime.fromtimestamp(a.expiry_time).strftime('%Y-%m-%d') }}</td><td class="asset-actions"><a href="{{ asset_relative_link }}" target="_blank" class="action-button btn-small btn-view">{{ lang['view'] }}</a><button onclick="copyLink('{{ asset_external_link }}')" class="action-button btn-small btn-link">Link</button>{% if a.type == 'domain' %}<a href="{{ url_for('edit_asset', asset_id=a.asset_id) }}" class="action-button btn-small btn-edit">{{ lang['edit'] }}</a>{% endif %}<form method="POST" style="display: inline-block;"><input type="hidden" name="action" value="delete_asset"><input type="hidden" name="asset_id" value="{{ a.asset_id }}"><button class="action-button btn-small btn-delete" type="submit">{{ lang['delete'] }}</button></form></td></tr>{% endfor %}</table></div><div class="card"><h3>{{ lang['last_transactions'] }}</h3><table><tr><th>{{ lang['tx_id'] }}</th> <th>{{ lang['tx_sender'] }}</th> <th>{{ lang['tx_recipient'] }}</th> <th>{{ lang['tx_amount'] }}</th> <th>{{ lang['tx_timestamp'] }}</th></tr>{% for tx in transactions %}<tr style="color: {% if tx.sender == user_ghst_address %}#f44336{% else %}#4CAF50{% endif %}"><td>{{ tx.tx_id[:8] }}...</td><td>{% if tx.sender == user_ghst_address %}SEN{% else %}{{ tx.sender[:8] }}...{% endif %}</td><td>{% if tx.recipient == user_ghst_address %}SEN{% else %}{{ tx.recipient[:8] }}...{% endif %}</td><td>{{ tx.amount | round(4) | thousands }}</td><td>{{ tx.timestamp | timestamp_to_datetime }}</td></tr>{% else %}<tr><td colspan="5">{{ lang['no_transactions'] }}</td></tr>{% endfor %}</table></div><div class="messenger-fab" onclick="toggleMessenger()">💬</div><div class="messenger-window" id="messengerWindow"><div class="msg-header"><span id="msgTitle" style="font-weight:bold; color:#00c853;">{{ lang['messenger_title'] }}</span><span onclick="toggleMessenger()" style="cursor:pointer; color:#888;">✖</span></div><div id="friendList" class="msg-body"><div style="padding:10px; border-bottom:1px solid #444; margin-bottom:10px;"><input type="text" id="inviteUser" placeholder="{{ lang['username'] }}" style="width:70%; display:inline-block;"><button onclick="inviteFriend()" class="action-button" style="width:25%; padding:8px; display:inline-block; margin-top:0;">+</button><div style="font-size:0.8em; color:#888; margin-top:5px;">{{ lang['msg_invite'] }}</div></div><div id="friendsContainer">Loading...</div></div><div id="chatView" class="msg-body" style="display:none; flex-direction:column;"><button onclick="showFriendList()" style="background:#444; border:none; color:white; width:100%; margin-bottom:10px; padding:5px; border-radius:5px; cursor:pointer;">&lt; {{ lang['msg_friends'] }}</button><div id="chatContainer" style="flex:1; overflow-y:auto; display:flex; flex-direction:column;"></div></div><div class="msg-footer" id="chatFooter" style="display:none;"><select id="assetAttach" style="width:40px; background:#333; color:white; border:1px solid #555; border-radius:4px;"><option value="">📎</option>{% for a in assets %}<option value="{{ a.asset_id }}">{{ a.name }}</option>{% endfor %}</select><input type="text" id="msgInput" placeholder="{{ lang['msg_placeholder'] }}" style="flex:1; margin:0;"><button onclick="sendMessage()" class="action-button" style="width:auto; padding:0 15px; margin:0;">➤</button></div></div><script>let currentFriendKey = null; function toggleMessenger() { let win = document.getElementById('messengerWindow'); win.style.display = win.style.display === 'none' ? 'flex' : 'none'; if(win.style.display === 'flex') loadFriends(); } function loadFriends() { fetch('/api/messenger/friends').then(r=>r.json()).then(data => { let html = ''; if(data.length === 0) html = '<div style="padding:10px; color:#888;">No friends yet.</div>'; data.forEach(f => { html += `<div class="friend-item" onclick="openChat('${f.friend_key}', '${f.username}')"><span style="font-size:1.2em; margin-right:10px;">👤</span> <span>${f.username}</span></div>`; }); document.getElementById('friendsContainer').innerHTML = html; }); } function inviteFriend() { let u = document.getElementById('inviteUser').value; if(!u) return; fetch('/api/messenger/invite', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username: u}) }).then(r=>r.json()).then(d => { alert(d.message); loadFriends(); document.getElementById('inviteUser').value=''; }); } function openChat(key, name) { currentFriendKey = key; document.getElementById('friendList').style.display = 'none'; document.getElementById('chatView').style.display = 'flex'; document.getElementById('chatFooter').style.display = 'flex'; document.getElementById('msgTitle').innerText = name; loadMessages(); } function showFriendList() { currentFriendKey = null; document.getElementById('friendList').style.display = 'block'; document.getElementById('chatView').style.display = 'none'; document.getElementById('chatFooter').style.display = 'none'; document.getElementById('msgTitle').innerText = "{{ lang['messenger_title'] }}"; } function loadMessages() { if(!currentFriendKey) return; fetch(`/api/messenger/chat/${currentFriendKey}`).then(r=>r.json()).then(data => { let html = ''; data.forEach(m => { let cls = m.sender === '{{ user_ghst_address }}' ? 'sent' : ''; let content = m.content; if(m.asset_id && m.asset_id !== 'null') content += ` <br><a href="/view_asset/${m.asset_id}" target="_blank" style="color:#00c853; font-weight:bold; text-decoration:none;">📎 [Dosya / File]</a>`; html += `<div class="msg-bubble ${cls}">${content}</div>`; }); document.getElementById('chatContainer').innerHTML = html; let container = document.getElementById('chatContainer'); container.scrollTop = container.scrollHeight; }); } function sendMessage() { let txt = document.getElementById('msgInput').value; let asset = document.getElementById('assetAttach').value; if(!txt && !asset) return; fetch('/api/messenger/send', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({recipient: currentFriendKey, content: txt, asset_id: asset}) }).then(r=>r.json()).then(d => { if(d.status === 'ok') { document.getElementById('msgInput').value = ''; document.getElementById('assetAttach').value = ''; loadMessages(); } else { alert(d.error); } }); } function toggleContractSection(section) { document.getElementById('contractDeploy').style.display = section === 'deploy' ? 'block' : 'none'; document.getElementById('contractInteract').style.display = section === 'interact' ? 'block' : 'none'; } setInterval(() => { if(document.getElementById('messengerWindow').style.display === 'flex' && currentFriendKey) { loadMessages(); } }, 5000);</script>{% endblock %}"""

# --- FLASK ROUTES AND CONFIG ---
app.jinja_loader = DictLoader({
    'base.html': LAYOUT, 
    'dashboard.html': DASHBOARD_UI, 
    'login.html': LOGIN_UI, 
    'register.html': REGISTER_UI, 
    'mining.html': MINING_UI, 
    'search.html': SEARCH_UI, 
    'edit_asset.html': EDIT_ASSET_UI
})

# Global Managers (Populated by Kivy App)
db = None
assets_mgr = None
blockchain_mgr = None
mesh_mgr = None
tx_mgr = None
smart_contract_mgr = None

@server.context_processor
def inject_globals():
    L = LANGUAGES.get(session.get('lang', 'tr'), LANGUAGES['tr'])
    return dict(lang=L)

@server.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in LANGUAGES: session['lang'] = lang
    return redirect(request.referrer or url_for('login'))

@server.route('/')
def index():
    if session.get('username'): return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@server.route('/login', methods=['GET', 'POST'])
def login():
    L = LANGUAGES[session.get('lang', 'tr')]
    if request.method == 'POST':
        conn = db.get_connection()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (request.form['username'], hashlib.sha256(request.form['password'].encode()).hexdigest())).fetchone()
        conn.close()
        if user:
            session['username'] = user['username']
            session['pub_key'] = user['wallet_public_key']
            session['pub_key_hash'] = user['wallet_public_key'][:20]
            session['balance'] = user['balance']
            return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_UI, lang=L, active_peers_count=0, stats=blockchain_mgr.get_statistics(), current_reward=50)

@server.route('/register', methods=['GET', 'POST'])
def register():
    L = LANGUAGES[session.get('lang', 'tr')]
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()
        public_key_hash, ghst_address = generate_user_keys(username)
        conn = db.get_connection()
        try:
            conn.execute("INSERT INTO users (username, password, wallet_public_key, balance) VALUES (?, ?, ?, ?)", (username, password, ghst_address, INITIAL_USER_BALANCE))
            conn.commit()
            session['username'] = username
            session['pub_key'] = ghst_address
            session['pub_key_hash'] = public_key_hash
            session['balance'] = INITIAL_USER_BALANCE
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError: pass
        finally: conn.close()
    return render_template_string(REGISTER_UI, lang=L, active_peers_count=0, stats=blockchain_mgr.get_statistics(), current_reward=50)

@server.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@server.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('username'): return redirect(url_for('login'))
    L = LANGUAGES[session.get('lang', 'tr')]
    pub_key = session['pub_key']
    message = None
    error = None
    contract_result = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'register_domain':
            success, msg = assets_mgr.register_asset(pub_key, 'domain', request.form['domain_name'], request.form.get('content'))
            if success: message = msg
            else: error = msg
        elif action == 'upload_media':
            f = request.files['file']
            if f.filename:
                success, msg = assets_mgr.register_asset(pub_key, 'file', f.filename, f, is_file=True)
                if success: message = msg
                else: error = msg
        elif action == 'delete_asset':
            success, msg = assets_mgr.delete_asset(request.form['asset_id'], pub_key)
            if success: message = msg
            else: error = msg
        elif action == 'send_coin':
            success, msg = blockchain_mgr.transfer_coin(pub_key, request.form['recipient'], float(request.form['amount']))
            if success: message = msg
            else: error = msg
        elif action == 'deploy_contract':
            code = request.form.get('code')
            success, res = smart_contract_mgr.deploy_contract(pub_key, code)
            if success: message = f"Contract Deployed: {res}"
            else: error = res
        elif action == 'call_contract':
            addr = request.form.get('contract_address')
            method = request.form.get('method')
            args = request.form.get('args')
            success, res = smart_contract_mgr.call_contract(pub_key, addr, method, args)
            if success: 
                message = "Contract Executed"
                contract_result = res
            else: error = res

    conn = db.get_connection()
    user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (pub_key,)).fetchone()
    session['balance'] = user['balance'] if user else 0.0
    assets = conn.execute("SELECT * FROM assets WHERE owner_pub_key = ? ORDER BY creation_time DESC", (pub_key,)).fetchall()
    conn.close()
    
    transactions = tx_mgr.get_last_transactions(pub_key)
    my_contracts = smart_contract_mgr.get_user_contracts(pub_key)
    
    return render_template_string(DASHBOARD_UI, lang=L, message=message, error=error, 
                                  user_ghst_address=pub_key, user_pub_key_hash=session.get('pub_key_hash'), 
                                  assets=assets, transactions=transactions, qr_code_link=generate_qr_code_link(pub_key), 
                                  DOMAIN_REGISTRATION_FEE=DOMAIN_REGISTRATION_FEE, calculate_asset_fee=calculate_asset_fee,
                                  active_peers_count=0, datetime=datetime,
                                  example_contract=EXAMPLE_CONTRACT, contract_result=contract_result,
                                  my_contracts=my_contracts)

@server.route('/mining', methods=['GET', 'POST'])
def mining():
    if not session.get('username'): return redirect(url_for('login'))
    L = LANGUAGES[session.get('lang', 'tr')]
    pub_key = session['pub_key']
    
    conn = db.get_connection()
    user = conn.execute("SELECT last_mined FROM users WHERE wallet_public_key = ?", (pub_key,)).fetchone()
    last_mined_time = user['last_mined'] if user else 0
    conn.close()
    
    can_mine = (time.time() - last_mined_time) >= 86400
    last_block = blockchain_mgr.get_last_block()
    current_reward = blockchain_mgr.calculate_block_reward(last_block['block_index'] + 1)
    
    message = None
    error = None

    if request.method == 'POST':
        if can_mine:
            result = blockchain_mgr.mine_block(pub_key)
            if result:
                message = L['mine_success']
                can_mine = False
                last_block = blockchain_mgr.get_last_block()
            else: error = "Mining error."
        else: error = L['mine_limit_error']

    remaining = max(0, 86400 - (time.time() - last_mined_time))
    remaining_time = str(timedelta(seconds=int(remaining)))
    stats = blockchain_mgr.get_statistics()
    
    return render_template_string(MINING_UI, lang=L, message=message, error=error, last_block=last_block, difficulty=4, current_reward=current_reward, can_mine=can_mine, remaining_time=remaining_time, stats=stats)

@app.route('/api/messenger/friends')
def api_friends():
    if not session.get('username'): return jsonify([])
    return jsonify(messenger_mgr.get_friends(session['pub_key']))

@app.route('/api/messenger/invite', methods=['POST'])
def api_invite():
    if not session.get('username'): return jsonify({'error': 'Auth required'}), 401
    data = request.json
    success, msg = messenger_mgr.send_invite(session['pub_key'], data.get('username'))
    return jsonify({'message': msg, 'status': 'ok' if success else 'error'})

@app.route('/api/messenger/chat/<friend_key>')
def api_chat(friend_key):
    if not session.get('username'): return jsonify([])
    return jsonify(messenger_mgr.get_messages(session['pub_key'], friend_key))

@app.route('/api/messenger/send', methods=['POST'])
def api_send_msg():
    if not session.get('username'): return jsonify({'error': 'Auth required'}), 401
    data = request.json
    success, msg = messenger_mgr.send_message(session['pub_key'], data.get('recipient'), data.get('content'), data.get('asset_id'))
    return jsonify({'status': 'ok' if success else 'error', 'error': msg})

# --- KIVY APP WRAPPER ---

class GhostMobileApp(App):
    def build(self):
        # TR: Uygulama başlatılırken veritabanı ve sunucu ayarlanır.
        # EN: Database and server are set up when app starts.
        global db_file_path, db, assets_mgr, blockchain_mgr, mesh_mgr, tx_mgr, smart_contract_mgr, messenger_mgr
        
        # TR: Android/iOS için yazılabilir veri yolu
        # EN: Writable data path for Android/iOS
        data_dir = self.user_data_dir
        db_file_path = os.path.join(data_dir, "ghost_mobile_v2.db")
        
        # Initialize Managers
        db = DatabaseManager(db_file_path)
        blockchain_mgr = BlockchainManager(db)
        assets_mgr = AssetManager(db)
        mesh_mgr = MeshManager(db)
        messenger_mgr = MessengerManager(db, blockchain_mgr, mesh_mgr)
        tx_mgr = TransactionManager(db)
        vm_engine = GhostVM()
        smart_contract_mgr = SmartContractManager(db, blockchain_mgr, vm_engine)
        
        # Start Flask in a background thread
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # UI
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        label = Label(text="[b]GhostProtocol Mobile Node[/b]\n\nRunning on Port 5000\nUncensorable. Unstoppable.", 
                      markup=True, halign='center', font_size='20sp')
        
        btn_open = Button(text="Open Dashboard / Paneli Aç", size_hint=(1, 0.2), background_color=(0, 0.8, 0.2, 1))
        btn_open.bind(on_press=self.open_browser)
        
        layout.add_widget(label)
        layout.add_widget(btn_open)
        
        return layout

    def run_server(self):
        # TR: Flask sunucusunu mobil cihazda başlatır.
        # EN: Starts Flask server on mobile device.
        server.run(host='0.0.0.0', port=GHOST_PORT, debug=False, use_reloader=False)

    def open_browser(self, instance):
        # TR: Yerel sunucuyu tarayıcıda açar.
        # EN: Opens local server in browser.
        webbrowser.open(f"http://127.0.0.1:{GHOST_PORT}")

if __name__ == '__main__':
    def format_thousands(value):
        try: return f"{float(value):,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except: return str(value)
    
    server.jinja_env.filters['thousands'] = format_thousands
    server.jinja_env.filters['timestamp_to_datetime'] = lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')

    GhostMobileApp().run()
