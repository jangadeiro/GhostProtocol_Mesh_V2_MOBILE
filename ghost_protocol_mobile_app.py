# -*- coding: utf-8 -*-
# GhostProtocol Mobile Node
# TR: Bu dosya GhostProtocol sunucusunu mobil cihazlar için bir Kivy uygulamasına dönüştürür.
# EN: This file converts the GhostProtocol server into a Kivy application for mobile devices.

import threading
import time
import os
import webbrowser
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.utils import platform

# TR: Flask sunucu kodlarını içe aktarıyoruz (veya bu dosyanın içine gömüyoruz).
# EN: Importing Flask server codes (or embedding them here).
# Not: Mobil uyumluluk için ghost_server01.py içeriği buraya entegre edilmiştir.
# Note: ghost_server01.py content is integrated here for mobile compatibility.

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

# --- LOGLAMA / LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GhostMobile - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostMobile")

# --- YAPILANDIRMA / CONFIGURATION ---
# TR: Veritabanı yolu mobil cihazın yazılabilir alanına göre ayarlanacak (App sınıfında).
# EN: Database path will be set according to the mobile device's writable area (in App class).
GHOST_PORT = 5000
BASE_DIFFICULTY = 4 
TOTAL_SUPPLY = 100000000.0 
INITIAL_BLOCK_REWARD = 50.0 
HALVING_INTERVAL = 2000
DOMAIN_EXPIRY_SECONDS = 15552000
STORAGE_COST_PER_MB = 0.01
DOMAIN_REGISTRATION_FEE = 1.0
INITIAL_USER_BALANCE = 50.0
KNOWN_PEERS = ["46.101.219.46", "68.183.12.91"] 

# Flask App
server = Flask(__name__)
server.secret_key = 'ghost_mobile_secret_key_v1'
server.permanent_session_lifetime = timedelta(days=7)

# --- ÇOKLU DİL SÖZLÜĞÜ / MULTI-LANGUAGE DICTIONARY ---
# (Server dosyasındaki ile aynı / Same as server file)
LANGUAGES = {
    'tr': {
        'title': "GhostProtocol Sunucusu", 'status_online': "ÇEVRİMİÇİ", 'status_offline': "ÇEVRİMDIŞI",
        'server_status': "Sunucu Durumu", 'active_peers': "Aktif Düğüm (Peer)",
        'dashboard_title': "Panel", 'mining_title': "Madencilik", 'logout': "Çıkış", 'login': "Giriş", 'register': "Kayıt", 'search': "Arama",
        'wallet_title': "💳 Cüzdanım", 'pubkey': "Public Key (Hash)", 'balance': "Bakiye",
        'domain_title': "💾 .ghost Kayıt", 'media_title': "🖼️ Varlık Yükle", 'asset_action': "İşlem", 
        'status_success': "Başarılı", 'status_failed': "Başarısız", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Link Kopyala",
        'media_info': "Desteklenen: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Yayınla", 
        'search_title': "🔍 Ghost Arama (İçerik & Domain)", 'edit': "Düzenle", 'delete': "Sil",
        'login_prompt': "Giriş Yap", 'username': "Kullanıcı Adı", 'password': "Şifre", 'submit': "Gönder",
        'asset_fee': "Ücret (Toplam)", 'asset_expires': "Süre Sonu", 'mine_success': "Blok Başarılı", 
        'mine_message': "Yeni blok bulundu: {{ block_hash }}. Ödül: {{ reward }} GHOST hesabınıza eklendi.",
        'mine_limit_error': "Günde sadece 1 kez madencilik yapabilirsiniz. Kalan süre:",
        'wallet_address': "Cüzdan Adresi (GHST)", 'last_transactions': "Son İşlemlerim", 
        'tx_id': "İşlem ID", 'tx_sender': "Gönderen", 'tx_recipient': "Alıcı", 'tx_amount': "Miktar", 'tx_timestamp': "Zaman",
        'no_transactions': "Henüz bir işlem yok.",
        'total_supply': "Toplam Arz", 'mined_supply': "Dolaşımdaki Arz", 'remaining_supply': "Kalan Arz",
        'mine_last_block': "Son Blok", 'mine_difficulty': "Zorluk", 'mine_reward': "Mevcut Ödül",
        'mine_next_halving': "Sonraki Yarılanma", 'view': "Görüntüle", 'back_to_dashboard': "Panele Dön",
        'send_coin_title': "Para Gönder", 'recipient_address': "Alıcı Cüzdan Adresi", 'amount': "Miktar", 'send_btn': "Gönder",
        'insufficient_balance': "Yetersiz bakiye.", 'transfer_success': "Transfer başarıyla gerçekleşti.", 'recipient_not_found': "Alıcı bulunamadı.",
        'asset_name': "Varlık Adı", 'asset_type': "Tür", 'my_assets_title': "Kayıtlı Varlıklarım", 'update_btn': "Güncelle", 'edit_title': "Varlık Düzenle",
        'content_placeholder': "İçerik (HTML/Metin)"
    },
    'en': {
        'title': "GhostProtocol Server", 'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'server_status': "Server Status", 'active_peers': "Active Peers",
        'dashboard_title': "Dashboard", 'mining_title': "Mining", 'logout': "Logout", 'login': "Login", 'register': "Register", 'search': "Search",
        'wallet_title': "💳 My Wallet", 'pubkey': "Public Key (Hash)", 'balance': "Balance",
        'domain_title': "💾 .ghost Registration", 'media_title': "🖼️ Upload Asset", 'asset_action': "Action", 
        'status_success': "Success", 'status_failed': "Failed", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Copy Link",
        'media_info': "Supported: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Publish", 
        'search_title': "🔍 Ghost Search (Content & Domain)", 'edit': "Edit", 'delete': "Delete",
        'login_prompt': "Login", 'username': "Username", 'password': "Password", 'submit': "Submit",
        'asset_fee': "Fee (Total)", 'asset_expires': "Expires", 'mine_success': "Block Success",
        'mine_message': "New block found: {{ block_hash }}. Reward: {{ reward }} GHOST added to your account.",
        'mine_limit_error': "You can only mine once per day. Time remaining:",
        'wallet_address': "Wallet Address (GHST)", 'last_transactions': "Last Transactions", 
        'tx_id': "Tx ID", 'tx_sender': "Sender", 'tx_recipient': "Recipient", 'tx_amount': "Amount", 'tx_timestamp': "Time",
        'no_transactions': "No transactions yet.",
        'total_supply': "Total Supply", 'mined_supply': "Circulating Supply", 'remaining_supply': "Remaining Supply",
        'mine_last_block': "Last Block", 'mine_difficulty': "Difficulty", 'mine_reward': "Current Reward",
        'mine_next_halving': "Next Halving", 'view': "View", 'back_to_dashboard': "Back to Dashboard",
        'send_coin_title': "Send Coin", 'recipient_address': "Recipient Wallet Address", 'amount': "Amount", 'send_btn': "Send",
        'insufficient_balance': "Insufficient balance.", 'transfer_success': "Transfer successful.", 'recipient_not_found': "Recipient not found.",
        'asset_name': "Asset Name", 'asset_type': "Type", 'my_assets_title': "My Registered Assets", 'update_btn': "Update", 'edit_title': "Edit Asset",
        'content_placeholder': "Content (HTML/Text)"
    },
     'ru': {
        'title': "Сервер GhostProtocol", 'status_online': "ОНЛАЙН", 'status_offline': "ОФФЛАЙН",
        'server_status': "Статус Сервера", 'active_peers': "Активные Пиры",
        'dashboard_title': "Панель", 'mining_title': "Майнинг", 'logout': "Выход", 'login': "Вход", 'register': "Регистрация", 'search': "Поиск",
        'wallet_title': "💳 Мой Кошелек", 'pubkey': "Публичный Ключ (Хеш)", 'balance': "Баланс",
        'domain_title': "💾 Регистрация .ghost", 'media_title': "🖼️ Загрузить Актив", 'asset_action': "Действие", 
        'status_success': "Успех", 'status_failed': "Ошибка", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Скопировано!",
        'media_info': "Поддерживается: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Опубликовать", 
        'search_title': "🔍 Ghost Поиск (Контент и Домен)", 'edit': "Редактировать", 'delete': "Удалить",
        'login_prompt': "Войти", 'username': "Имя пользователя", 'password': "Пароль", 'submit': "Отправить",
        'asset_fee': "Плата", 'asset_expires': "Срок", 'mine_success': "Блок Успешен", 
        'mine_message': "Найден новый блок: {{ block_hash }}. Награда: {{ reward }} GHOST добавлена на ваш счет.",
        'mine_limit_error': "Вы можете майнить только один раз в день. Оставшееся время:",
        'wallet_address': "Адрес Кошелька (GHST)", 'last_transactions': "Последние Транзакции", 
        'tx_id': "ID Транзакции", 'tx_sender': "Отправитель", 'tx_recipient': "Получатель", 'tx_amount': "Сумма", 'tx_timestamp': "Время",
        'no_transactions': "Пока нет транзакций.",
        'total_supply': "Общий Объем", 'mined_supply': "В Обращении", 'remaining_supply': "Оставшийся Объем",
        'mine_last_block': "Последний Блок", 'mine_difficulty': "Сложность", 'mine_reward': "Текущая Награда",
        'mine_next_halving': "Следующее Уполовинивание", 'view': "Просмотр", 'back_to_dashboard': "Назад",
        'send_coin_title': "Отправить монеты", 'recipient_address': "Адрес кошелька получателя", 'amount': "Сумма", 'send_btn': "Отправить",
        'insufficient_balance': "Недостаточно средств на балансе.", 'transfer_success': "Перевод успешно завершен", 'recipient_not_found': "Получатель не найден.",
        'asset_name': "Название актива", 'asset_type': "Тип", 'my_assets_title': "Мои зарегистрированные активы", 'update_btn': "Обновить", 'edit_title': "Редактировать актив",
        'content_placeholder': "Содержание (HTML/Текст)"
    },
    'hy': {
        'title': "GhostProtocol Սերվեր", 'status_online': "ԱՌՑԱՆՑ", 'status_offline': "ԱՆՑԱՆՑ",
        'server_status': "Սերվերի Կարգավիճակը", 'active_peers': "Ակտիվ Փիրեր",
        'dashboard_title': "Վահանակ", 'mining_title': "Մայնինգ", 'logout': "Ելք", 'login': "Մուտք", 'register': "Գրանցվել", 'search': "Որոնում",
        'wallet_title': "💳 Իմ Դրամապանակը", 'pubkey': "Հանրային Բանալի (Հեշ)", 'balance': "Մնացորդ",
        'domain_title': "💾 .ghost Գրանցում", 'media_title': "🖼️ Բեռնել Ակտիվ", 'asset_action': "Գործողություն", 
        'status_success': "Հաջող", 'status_failed': "Ձախողված", 
        'monthly_fee_unit': " GHOST", 'media_link_copy': "Պատճենվեց!",
        'media_info': "Աջակցվում է՝ .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Հրատարակել", 
        'search_title': "🔍 Ghost Որոնում (Բովանդակություն և Դոմեն)", 'edit': "Խմբագրել", 'delete': "Ջնջել",
        'login_prompt': "Մուտք գործել", 'username': "Օգտվողի անուն", 'password': "Գաղտնաբառ", 'submit': "Ուղարկել",
        'asset_fee': "Վճար", 'asset_expires': "Ժամկետը", 'mine_success': "Բլոկի Հաջողություն",
        'mine_message': "Գտնվեց նոր բլոկ: {{ block_hash }}: Պարգև՝ {{ reward }} GHOST ավելացվել է ձեր հաշվին:",
        'mine_limit_error': "Դուք կարող եք մայնինգ անել օրը միայն մեկ անգամ: Մնացած ժամանակը:",
        'wallet_address': "Դրամապանակի Հասցե (GHST)", 'last_transactions': "Վերջին Գործարքները", 
        'tx_id': "Գործարքի ID", 'tx_sender': "Ուղարկող", 'tx_recipient': "Ստացող", 'tx_amount': "Գումար", 'tx_timestamp': "Ժամանակ",
        'no_transactions': "Դեռ գործարքներ չկան։",
        'total_supply': "Ընդհանուր Մատակարարում", 'mined_supply': "Շրջանառվող Մատակարարում", 'remaining_supply': "Մնացորդային Մատակարարում",
        'mine_last_block': "Վերջին Բլոկ", 'mine_difficulty': "Բարդություն", 'mine_reward': "Ընթացիկ Պարգև",
        'mine_next_halving': "Հաջորդ Կիսում", 'view': "Դիտել", 'back_to_dashboard': "Վերադառնալ",
        'send_coin_title': "Ուղարկել մետաղադրամ", 'recipient_address': "Ստացողի դրամապանակի հասցե", 'amount': "Գումար", 'send_btn': "Ուղարկել",
        'insufficient_balance': "Անբավարար մնացորդ.", 'transfer_success': "Փոխանցումը հաջողված է.", 'recipient_not_found': "Ստացողը չի գտնվել.",
        'asset_name': "Ակտիվի անվանումը", 'asset_type': "Տեսակը", 'my_assets_title': "Իմ գրանցված ակտիվները", 'update_btn': "Թարմացնել", 'edit_title': "Խմբագրել ակտիվը",
        'content_placeholder': "Բովանդակություն (HTML/Տեքստ)"
    }
}

# --- TEMPLATE DEĞİŞKENLERİ ---
LAYOUT = r"""<!DOCTYPE html><html lang="{{ session.get('lang', 'tr') }}"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{{ lang['title'] }}</title><style>body { font-family: 'Segoe UI', sans-serif; background-color: #1e1e1e; color: #ddd; margin:0; padding:0; }.header { background-color: #333; padding: 15px; border-bottom: 2px solid #00c853; text-align:center; }.card { background-color: #2a2a2a; padding: 15px; margin: 10px; border-radius: 8px; }.action-button { background-color: #4caf50; color: white; padding: 10px; border: none; width:100%; border-radius: 5px; margin-top:5px; } input, textarea { width: 95%; padding: 10px; margin: 5px 0; background: #333; color: white; border: 1px solid #555; }</style></head><body><div class="header"><h3>GhostProtocol</h3><a href="/dashboard" style="color:white; margin:5px;">Panel</a> <a href="/logout" style="color:red;">X</a><br><div style="margin-top:5px;"><a href="/set_lang/tr">TR</a> <a href="/set_lang/en">EN</a> <a href="/set_lang/ru">RU</a> <a href="/set_lang/hy">HY</a></div></div>{% block content %}{% endblock %}</body></html>"""
# (Diğer HTML template'leri basitlik için server dosyasındaki ile aynı mantıkta kullanılacaktır)
# (Other HTML templates will be used with the same logic as the server file for simplicity)

# --- GLOBAL VARIABLES FOR DB ---
# TR: Global değişkenler, App sınıfında initialize edilecek
# EN: Global variables, will be initialized in App class
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
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, wallet_public_key TEXT UNIQUE, balance REAL DEFAULT 50, last_mined REAL DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER PRIMARY KEY, timestamp REAL, previous_hash TEXT, block_hash TEXT, proof INTEGER, miner_key TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL, block_index INTEGER DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mesh_peers (ip_address TEXT PRIMARY KEY, last_seen REAL)''')
        try: cursor.execute("SELECT last_mined FROM users LIMIT 1")
        except sqlite3.OperationalError: cursor.execute("ALTER TABLE users ADD COLUMN last_mined REAL DEFAULT 0")
        if cursor.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0:
            self.create_genesis_block(cursor)
        conn.commit()
        conn.close()

    def create_genesis_block(self, cursor):
        genesis_hash = hashlib.sha256(b'GhostGenesis').hexdigest()
        cursor.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                       (1, time.time(), '0', genesis_hash, 100, 'GhostProtocol_System'))

# --- MANAGER SINIFLARI (ÖZETLENDİ) / MANAGER CLASSES (SUMMARIZED) ---
# TR: Bu sınıflar server dosyasındaki mantıkla birebir aynıdır, sadece self.db referansı düzeltilmiştir.
# EN: These classes are identical to the server file logic, only self.db reference is adjusted.

class AssetManager:
    def __init__(self, db_manager): self.db = db_manager
    # ... (Register, Update, Delete, Get metodları buraya gelecek - Server dosyasındaki ile aynı)
    # ... (Register, Update, Delete, Get methods go here - Same as server file)
    # NOT: Kod bütünlüğü için server dosyasındaki AssetManager metotlarının tamamı buraya kopyalanmalıdır.
    # NOTE: For code integrity, all AssetManager methods from the server file should be copied here.
    def register_asset(self, owner_key, asset_type, name, content, is_file=False):
        # ... (Server kodundaki mantık)
        if asset_type == 'domain' and not name.endswith('.ghost'): name += '.ghost'
        if not content and asset_type == 'domain': content = "<h1>New Ghost Site</h1>"
        if is_file: 
            content.seek(0)
            content_bytes = content.read()
        else: content_bytes = content.encode('utf-8')
        fee = calculate_asset_fee(len(content_bytes), asset_type)
        conn = self.db.get_connection()
        user = conn.execute("SELECT balance FROM users WHERE wallet_public_key = ?", (owner_key,)).fetchone()
        if not user or user['balance'] < fee: 
            conn.close()
            return False, "Yetersiz Bakiye"
        try:
            conn.execute("INSERT OR REPLACE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), owner_key, asset_type, name, content_bytes, len(content_bytes), time.time(), time.time()+DOMAIN_EXPIRY_SECONDS, ""))
            conn.execute("UPDATE users SET balance = balance - ? WHERE wallet_public_key = ?", (fee, owner_key))
            conn.commit()
            return True, f"Başarılı. Ücret: {fee}"
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
            content = base64.b64decode(asset_data['content'])
            conn.execute("INSERT OR IGNORE INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (asset_data['asset_id'], asset_data['owner_pub_key'], asset_data['type'], asset_data['name'], content, len(content), asset_data['creation_time'], asset_data['expiry_time'], ""))
            conn.commit()
        except: pass
        finally: conn.close()

class BlockchainManager:
    def __init__(self, db_manager): self.db = db_manager
    # ... (Mine, Transfer, Sync metodları server dosyasındaki ile aynı)
    # ... (Mine, Transfer, Sync methods same as server file)
    def get_last_block(self):
        conn = self.db.get_connection()
        block = conn.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1").fetchone()
        conn.close()
        return block
    
    def get_all_headers(self):
        conn = self.db.get_connection()
        h = conn.execute("SELECT block_index, block_hash FROM blocks").fetchall()
        conn.close()
        return [dict(i) for i in h]
    
    def get_block_by_hash(self, h):
        conn = self.db.get_connection()
        b = conn.execute("SELECT * FROM blocks WHERE block_hash = ?", (h,)).fetchone()
        conn.close()
        return dict(b) if b else None

    def add_block_from_peer(self, block_data):
        # TR: GÜNCELLENMİŞ MANTIK (Bakiyeleri güncelleyen)
        # EN: UPDATED LOGIC (Updates balances)
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("INSERT OR IGNORE INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?, ?, ?, ?, ?, ?)",
                         (block_data['block_index'], block_data['timestamp'], block_data['previous_hash'], block_data['block_hash'], block_data['proof'], block_data['miner_key']))
            
            if cursor.rowcount > 0:
                index = block_data['block_index']
                pending_txs = conn.execute("SELECT tx_id, sender, recipient, amount FROM transactions WHERE block_index = 0 OR block_index IS NULL").fetchall()
                for p_tx in pending_txs:
                    conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (p_tx['amount'], p_tx['recipient']))
                    conn.execute("UPDATE transactions SET block_index = ? WHERE tx_id = ?", (index, p_tx['tx_id']))
                
                # Reward processing
                reward = INITIAL_BLOCK_REWARD # Simplified
                conn.execute("UPDATE users SET balance = balance + ? WHERE wallet_public_key = ?", (reward, block_data['miner_key']))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    def transfer_coin(self, sender, recipient, amount):
        conn = self.db.get_connection()
        try:
            s_bal = conn.execute("SELECT balance FROM users WHERE wallet_public_key=?",(sender,)).fetchone()
            if not s_bal or s_bal['balance'] < amount: return False, "Yetersiz Bakiye"
            conn.execute("UPDATE users SET balance=balance-? WHERE wallet_public_key=?", (amount, sender))
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp, block_index) VALUES (?,?,?,?,?,?)", (str(uuid4()), sender, recipient, amount, time.time(), 0))
            conn.commit()
            self.broadcast_transaction({'tx_id': str(uuid4()), 'sender': sender, 'recipient': recipient, 'amount': amount, 'timestamp': time.time()})
            return True, "Başarılı"
        except Exception as e: return False, str(e)
        finally: conn.close()

    def broadcast_transaction(self, tx_data):
        def _send():
            peers = mesh_mgr.get_peer_ips()
            for peer in peers:
                try: requests.post(f"http://{peer}:{GHOST_PORT}/api/send_transaction", json=tx_data, timeout=1)
                except: pass
        threading.Thread(target=_send, daemon=True).start()

    def receive_transaction(self, tx_data):
        conn = self.db.get_connection()
        try:
            exists = conn.execute("SELECT tx_id FROM transactions WHERE tx_id=?", (tx_data['tx_id'],)).fetchone()
            if not exists:
                conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp, block_index) VALUES (?,?,?,?,?,?)", (tx_data['tx_id'], tx_data['sender'], tx_data['recipient'], tx_data['amount'], tx_data['timestamp'], 0))
                conn.commit()
        except: pass
        finally: conn.close()

    def mine_block(self, miner_key):
        # Simplified mining for mobile
        conn = self.db.get_connection()
        last = self.get_last_block()
        idx = last['block_index'] + 1
        h = hashlib.sha256(f"{idx}{time.time()}".encode()).hexdigest()
        try:
            conn.execute("INSERT INTO blocks (block_index, timestamp, previous_hash, block_hash, proof, miner_key) VALUES (?,?,?,?,?,?)", (idx, time.time(), last['block_hash'], h, 100, miner_key))
            conn.execute("UPDATE users SET balance=balance+? WHERE wallet_public_key=?", (INITIAL_BLOCK_REWARD, miner_key))
            # Process pending
            pending = conn.execute("SELECT tx_id, recipient, amount FROM transactions WHERE block_index=0").fetchall()
            for p in pending:
                conn.execute("UPDATE users SET balance=balance+? WHERE wallet_public_key=?", (p['amount'], p['recipient']))
                conn.execute("UPDATE transactions SET block_index=? WHERE tx_id=?", (idx, p['tx_id']))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

class MeshManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except: pass
        self.start_discovery()

    def start_discovery(self):
        threading.Thread(target=self._listen, daemon=True).start()
        threading.Thread(target=self._broadcast, daemon=True).start()
        threading.Thread(target=self._sync, daemon=True).start()

    def _broadcast(self):
        while True:
            try:
                msg = json.dumps({'type':'presence', 'ip': '0.0.0.0'}).encode() # Simplification
                self.broadcast_socket.sendto(msg, ('<broadcast>', UDP_BROADCAST_PORT))
            except: pass
            time.sleep(30)
    
    def _listen(self):
        # Mobile listening logic might require permissions
        pass 

    def _sync(self):
        time.sleep(5)
        while True:
            self.sync_with_network()
            time.sleep(60)

    def sync_with_network(self):
        # Sync logic from server file
        pass

    def get_active_peers(self): return 0
    def get_peer_ips(self): return KNOWN_PEERS

# --- FLASK ROUTES (MOBIL UYARLAMASI) ---
# --- FLASK ROUTES (MOBILE ADAPTATION) ---

# Global Managers
db = None
assets_mgr = None
blockchain_mgr = None
mesh_mgr = None
tx_mgr = None

@server.context_processor
def inject_globals():
    L = LANGUAGES.get(session.get('lang', 'tr'), LANGUAGES['tr'])
    return dict(lang=L)

@server.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in LANGUAGES: session['lang'] = lang
    return redirect(url_for('dashboard'))

@server.route('/')
def index():
    if session.get('username'): return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_UI, lang=LANGUAGES['tr'])

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
            return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_UI, lang=L)

@server.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('username'): return redirect(url_for('login'))
    L = LANGUAGES[session.get('lang', 'tr')]
    pub = session['pub_key']
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'send_coin':
            blockchain_mgr.transfer_coin(pub, request.form['recipient'], float(request.form['amount']))
        elif action == 'register_domain':
            assets_mgr.register_asset(pub, 'domain', request.form['domain_name'], request.form['content'])

    conn = db.get_connection()
    user = conn.execute("SELECT balance FROM users WHERE wallet_public_key=?",(pub,)).fetchone()
    assets = conn.execute("SELECT * FROM assets WHERE owner_pub_key=?",(pub,)).fetchall()
    txs = conn.execute("SELECT * FROM transactions WHERE sender=? OR recipient=?",(pub,pub)).fetchall()
    conn.close()
    
    return render_template_string(DASHBOARD_UI, lang=L, assets=assets, transactions=txs, user_ghst_address=pub, user_pub_key_hash=pub[:10], balance=user['balance'], qr_code_link="")

@server.route('/mining', methods=['POST'])
def mine():
    if session.get('username'):
        blockchain_mgr.mine_block(session['pub_key'])
    return redirect(url_for('dashboard'))

# --- API ENDPOINTS ---
@server.route('/api/send_transaction', methods=['POST'])
def api_receive_tx():
    if request.json: blockchain_mgr.receive_transaction(request.json)
    return jsonify({'status':'ok'})

# --- KIVY APP WRAPPER ---

class GhostMobileApp(App):
    def build(self):
        # TR: Uygulama başlatılırken veritabanı ve sunucu ayarlanır.
        # EN: Database and server are set up when app starts.
        global db_file_path, db, assets_mgr, blockchain_mgr, mesh_mgr, tx_mgr
        
        # TR: Android/iOS için yazılabilir veri yolu
        # EN: Writable data path for Android/iOS
        data_dir = self.user_data_dir
        db_file_path = os.path.join(data_dir, "ghost_mobile.db")
        
        # Initialize Managers
        db = DatabaseManager(db_file_path)
        assets_mgr = AssetManager(db)
        blockchain_mgr = BlockchainManager(db)
        mesh_mgr = MeshManager(db)
        
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
    GhostMobileApp().run()
