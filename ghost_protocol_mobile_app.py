# ghost_protocol_mobile_app.py
import hashlib
import json
import time
import sqlite3
import base64
import random
import re
import logging
import os
import requests 
from uuid import uuid4
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from datetime import timedelta, datetime
from typing import Dict, Any, List, Optional, Tuple

# --- LOGLAMA / LOGGING ---
# TR: Mobil cihazlar için basit loglama yapılandırması.
# EN: Simple logging configuration for mobile devices.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GhostMobile - %(levelname)s - %(message)s')
logger = logging.getLogger("GhostMobile")

# --- YAPILANDIRMA / CONFIGURATION (ghost_server.py ile Eşleşmeli) ---
BASE_DIFFICULTY = 4 
TOTAL_SUPPLY = 100000000.0 
INITIAL_BLOCK_REWARD = 50.0 
HALVING_INTERVAL = 2000
# TR: Mobil cihazda yerel veritabanı dosyası
# EN: Local database file on the mobile device
DB_FILE = "ghost_mobile_data.db" 
DOMAIN_EXPIRY_SECONDS = 15552000 
STORAGE_COST_PER_MB = 0.01        
DOMAIN_REGISTRATION_FEE = 1.0     
INITIAL_USER_BALANCE = 50.0 
# TR: Ağdaki bilinen merkezi sunucular (Node'ların bağlanacağı Backbone sunucular)
# EN: Known central servers (Backbone servers that Nodes will connect to)
KNOWN_SERVERS = ["http://127.0.0.1:5000", "http://your.main.server.ip:5000"] 

# --- ÇOKLU DİL SÖZLÜĞÜ / MULTI-LANGUAGE DICTIONARY (ghost_server.py'den Alındı) ---
# TR: Tüm çeviriler (arayüz metinleri) buradadır.
# EN: All translations (UI texts) are located here.
LANGUAGES = {
    'tr': {
        'title': "GhostProtocol Mobil", 'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'dashboard_title': "Panel", 'mining_title': "Madencilik", 'logout': "Çıkış", 'login': "Giriş", 'register': "Kayıt", 'search': "Arama",
        'wallet_title': "💳 Cüzdanım", 'pubkey': "Public Key (Hash)", 'balance': "Bakiye",
        'domain_title': "💾 .ghost Kayıt", 'media_title': "🖼️ Varlık Yükle", 'asset_action': "İşlem", 
        'status_success': "Başarılı", 'status_failed': "Başarısız", 
        'not_logged_in': "Lütfen giriş yapın veya kayıt olun.",
        'media_info': "Desteklenen: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Yayınla", 
        'search_title': "🔍 Ghost Arama", 'edit': "Düzenle", 'delete': "Sil",
        'login_prompt': "Giriş Yap", 'username': "Kullanıcı Adı", 'password': "Şifre", 'submit': "Gönder",
        'asset_fee': "Ücret", 'asset_expires': "Süre Sonu", 'mine_success': "Blok Başarılı", 
        'mine_message': "Yeni blok bulundu: {{ block_hash }}. Ödül: {{ reward }} GHOST hesabınıza eklendi.",
        'mine_limit_error': "Günde sadece 1 kez madencilik yapabilirsiniz. Kalan süre:",
        'wallet_address': "Cüzdan Adresi (GHST)", 'last_transactions': "Son İşlemlerim", 
        'tx_id': "İşlem ID", 'tx_sender': "Gönderen", 'tx_recipient': "Alıcı", 'tx_amount': "Miktar", 'tx_timestamp': "Zaman",
        'no_transactions': "Henüz bir işlem yok.",
        'total_supply': "Toplam Arz", 'mined_supply': "Dolaşımdaki Arz", 'remaining_supply': "Kalan Arz",
        'mine_last_block': "Son Blok", 'mine_difficulty': "Zorluk", 'mine_reward': "Mevcut Ödül",
        'mine_next_halving': "Sonraki Yarılanma",
        'backbone_sync': "Backbone Sunucu Senkronizasyonu",
        'sync_success': "Senkronizasyon Başarılı. Yeni Blok Sayısı: "
    },
    'en': {
        'title': "GhostProtocol Mobile", 'status_online': "ONLINE", 'status_offline': "OFFLINE",
        'dashboard_title': "Dashboard", 'mining_title': "Mining", 'logout': "Logout", 'login': "Login", 'register': "Register", 'search': "Search",
        'wallet_title': "💳 My Wallet", 'pubkey': "Public Key (Hash)", 'balance': "Balance",
        'domain_title': "💾 .ghost Registration", 'media_title': "🖼️ Upload Asset", 'asset_action': "Action", 
        'status_success': "Success", 'status_failed': "Failed", 
        'not_logged_in': "Please login or register.",
        'media_info': "Supported: .png, .jpg, .css, .js, .woff, .mp4, .mp3", 'register_btn': "Publish", 
        'search_title': "🔍 Ghost Search", 'edit': "Edit", 'delete': "Delete",
        'login_prompt': "Login", 'username': "Username", 'password': "Password", 'submit': "Submit",
        'asset_fee': "Fee", 'asset_expires': "Expires", 'mine_success': "Block Success",
        'mine_message': "New block found: {{ block_hash }}. Reward: {{ reward }} GHOST added to your account.",
        'mine_limit_error': "You can only mine once per day. Time remaining:",
        'wallet_address': "Wallet Address (GHST)", 'last_transactions': "Last Transactions", 
        'tx_id': "Tx ID", 'tx_sender': "Sender", 'tx_recipient': "Recipient", 'tx_amount': "Amount", 'tx_timestamp': "Time",
        'no_transactions': "No transactions yet.",
        'total_supply': "Total Supply", 'mined_supply': "Circulating Supply", 'remaining_supply': "Remaining Supply",
        'mine_last_block': "Last Block", 'mine_difficulty': "Difficulty", 'mine_reward': "Current Reward",
        'mine_next_halving': "Next Halving",
        'backbone_sync': "Backbone Server Sync",
        'sync_success': "Synchronization Successful. New Block Count: "
    },
    # ... Diğer diller (RU, HY) ghost_server.py'den tamamen aktarılmıştır.
}

# --- YARDIMCI FONKSİYONLAR / UTILITY FUNCTIONS ---

def calculate_asset_fee(size_bytes: int, asset_type: str) -> float:
    # TR: Varlık ücretini hesaplar (Domain 1.0 GHOST, diğerleri MB başına).
    # EN: Calculates the asset fee (Domain 1.0 GHOST, others per MB).
    if asset_type == 'domain':
        return DOMAIN_REGISTRATION_FEE
    else:
        return round((size_bytes / (1024 * 1024)) * STORAGE_COST_PER_MB, 5)

def extract_keywords(content_str: str) -> str:
    # TR: HTML içeriğinden anahtar kelimeleri çıkarır.
    # EN: Extracts keywords from HTML content.
    try:
        text = re.sub(r'<(script|style).*?>.*?</\1>', '', content_str, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<.*?>', ' ', text)
        text = re.sub(r'[^a-zA-ZğüşıöçĞÜŞİÖÇ ]', ' ', text)
        words = text.lower().split()
        stop_words = {'ve', 'ile', 'the', 'and', 'for', 'this', 'bir', 'için', 'or', 'by', 'of'}
        keywords = set([w for w in words if len(w) > 2 and w not in stop_words])
        return ",".join(list(keywords)[:20])
    except:
        return ""

# --- TEMEL YÖNETİCİ SINIFLARI / CORE MANAGER CLASSES (ghost_server.py'den adapte edilmiştir) ---

class DatabaseManager:
    # TR: SQLite veritabanı işlemlerini yönetir.
    # EN: Manages SQLite database operations.
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        # Mobil uygulamada threading kullanabileceği için check_same_thread=False eklenmiştir.
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=20) 
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Kullanıcılar, Varlıklar, Blockchain, Peer tabloları ghost_server.py'deki gibi oluşturulur.
        # ... (Tam tablo oluşturma SQL'leri yer kaplamamak için burada gösterilmemiştir, server kodundan alınmıştır)
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, pub_key TEXT, priv_key TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, owner_pub_key TEXT, type TEXT, name TEXT, content BLOB, storage_size INTEGER, creation_time REAL, expiry_time REAL, keywords TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS blockchain (index INTEGER PRIMARY KEY, timestamp REAL, transactions TEXT, proof INTEGER, previous_hash TEXT, hash TEXT, mined_by TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, amount REAL, timestamp REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_config (key TEXT PRIMARY KEY, value TEXT)''')
        
        # Başlangıç Kullanıcı Kaydı (Varsayılan Admin / Test Kullanıcısı)
        # Sadece ilk çalıştırmada Genesis blok oluşturulur.
        if cursor.execute("SELECT COUNT(*) FROM blockchain").fetchone()[0] == 0:
            # Genesis Blok
            genesis_hash = hashlib.sha256("GenesisBlock_GhostProtocol_v1".encode()).hexdigest()
            cursor.execute("INSERT INTO blockchain (index, timestamp, transactions, proof, previous_hash, hash, mined_by) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           (1, time.time(), '[]', 1, '0', genesis_hash, 'GhostProtocol_System'))
            
            # Test Kullanıcısı ve Bakiye (Mobil cihazın sahibi)
            test_username = "mobile_user"
            test_password = hashlib.sha256("password123".encode()).hexdigest()
            # Yeni bir anahtar çifti oluşturma simülasyonu
            test_pub_key = f"GHST{hashlib.sha256(test_username.encode()).hexdigest()[:20]}"
            
            cursor.execute("INSERT OR IGNORE INTO users (username, password_hash, pub_key, priv_key) VALUES (?, ?, ?, ?)", 
                           (test_username, test_password, test_pub_key, "simulated_priv_key"))
            
            # Başlangıç bakiyesi
            cursor.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                           (str(uuid4()), "System", test_pub_key, INITIAL_USER_BALANCE, time.time()))
            
            # Aktif kullanıcıyı kaydet (session yerine)
            cursor.execute("INSERT OR REPLACE INTO user_config (key, value) VALUES (?, ?)", ('active_user_pub_key', test_pub_key))
            cursor.execute("INSERT OR REPLACE INTO user_config (key, value) VALUES (?, ?)", ('lang', 'tr'))

        conn.commit()
        conn.close()

    def get_config(self, key):
        # ...
        conn = self.get_connection()
        result = conn.execute("SELECT value FROM user_config WHERE key = ?", (key,)).fetchone()
        conn.close()
        return result['value'] if result else None

    def set_config(self, key, value):
        # ...
        conn = self.get_connection()
        conn.execute("INSERT OR REPLACE INTO user_config (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()

# Diğer Manager Sınıfları (UserManager, BlockchainManager, AssetManager, MeshManager) 
# Flask bağımlılıkları olmadan ghost_server.py'den tamamen korunur.
# Sadece `get_current_user_pub_key` gibi bir mekanizma eklenir.

class UserManager:
    # ... (Kayıt, Giriş, Anahtar üretme mantığı korunur)
    def __init__(self, db_manager):
        self.db = db_manager

    def get_user_by_pubkey(self, pub_key):
        conn = self.db.get_connection()
        user = conn.execute("SELECT * FROM users WHERE pub_key = ?", (pub_key,)).fetchone()
        conn.close()
        return dict(user) if user else None

    # ... (Diğer tüm UserManager metotları korunur)

class BlockchainManager:
    # ... (Blok, İşlem, Madencilik mantığı korunur)
    def __init__(self, db_manager):
        self.db = db_manager

    def get_balance(self, pub_key: str) -> float:
        # ... (Bakiye hesaplama mantığı korunur)
        conn = self.db.get_connection()
        
        # Gelen (Mined + Received)
        received = conn.execute("SELECT SUM(amount) FROM transactions WHERE recipient = ?", (pub_key,)).fetchone()[0] or 0.0
        
        # Giden (Sent)
        sent = conn.execute("SELECT SUM(amount) FROM transactions WHERE sender = ?", (pub_key,)).fetchone()[0] or 0.0
        
        conn.close()
        return received - sent

    # ... (Diğer tüm BlockchainManager metotları korunur)

class AssetManager:
    # ... (Varlık kayıt, silme mantığı korunur)
    def __init__(self, db_manager):
        self.db = db_manager

    def register_asset(self, owner_key, asset_type, name, content, storage_size, keywords=""):
        # TR: Varlık kayıt mantığı (Ücret kesme dahil) korunur.
        # EN: Asset registration logic (including fee deduction) is preserved.
        conn = self.db.get_connection()
        blockchain_mgr = BlockchainManager(self.db)
        
        fee = calculate_asset_fee(storage_size, asset_type)
        current_balance = blockchain_mgr.get_balance(owner_key)

        if current_balance < fee:
            conn.close()
            return False, f"Insufficient balance: {fee:.4f} GHOST required."

        asset_id = str(uuid4())
        expiry_time = time.time() + DOMAIN_EXPIRY_SECONDS
        
        try:
            # Asset Kaydı
            conn.execute("INSERT INTO assets (asset_id, owner_pub_key, type, name, content, storage_size, creation_time, expiry_time, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (asset_id, owner_key, asset_type, name, content, storage_size, time.time(), expiry_time, keywords))
            
            # İşlem Kaydı (Ücret Kesintisi)
            conn.execute("INSERT INTO transactions (tx_id, sender, recipient, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                         (str(uuid4()), owner_key, "GhostProtocol_Fee_Wallet", fee, time.time()))
            
            conn.commit()
            return True, "Asset registered and fee deducted successfully."
        except Exception as e:
            logger.error(f"Asset registration error: {e}")
            return False, str(e)
        finally:
            conn.close()

    # ... (Diğer tüm AssetManager metotları korunur)


class MobileBackend:
    # TR: Mobil arayüzün etkileşim kuracağı ana sınıf. Durumu (dil, kullanıcı) bu sınıf yönetir.
    # EN: The main class the mobile UI will interact with. Manages state (language, user).
    def __init__(self):
        self.db = DatabaseManager(DB_FILE)
        self.user_mgr = UserManager(self.db)
        self.chain_mgr = BlockchainManager(self.db)
        self.asset_mgr = AssetManager(self.db)
        # MeshManager'ı mobil cihazlar için sadece merkezi sunucuya bağlanacak şekilde kullanacağız.
        self.servers = KNOWN_SERVERS
        self.active_user_pub_key = self.db.get_config('active_user_pub_key')
        self.lang_code = self.db.get_config('lang') or 'tr'
        self.L = LANGUAGES.get(self.lang_code, LANGUAGES['tr'])
        logger.info(f"Ghost Mobile Backend Initialized for user: {self.active_user_pub_key}")

    def get_current_user_state(self) -> Dict[str, Any]:
        # TR: Arayüzün görüntüleyeceği temel kullanıcı verilerini hazırlar.
        # EN: Prepares the basic user data for the UI to display.
        if not self.active_user_pub_key:
            return {'logged_in': False, 'message': self.L['not_logged_in']}

        balance = self.chain_mgr.get_balance(self.active_user_pub_key)
        
        # Yerel varlıkları çek
        conn = self.db.get_connection()
        assets = conn.execute("SELECT asset_id, type, name, storage_size, expiry_time FROM assets WHERE owner_pub_key = ? ORDER BY creation_time DESC", (self.active_user_pub_key,)).fetchall()
        transactions = conn.execute("SELECT * FROM transactions WHERE sender = ? OR recipient = ? ORDER BY timestamp DESC LIMIT 10", (self.active_user_pub_key, self.active_user_pub_key)).fetchall()
        conn.close()

        # Sonuçları Dict listesine çevir
        asset_list = [dict(a) for a in assets]
        tx_list = [dict(t) for t in transactions]

        return {
            'logged_in': True,
            'lang': self.L,
            'pub_key': self.active_user_pub_key,
            'balance': round(balance, 4),
            'assets': asset_list,
            'transactions': tx_list,
        }

    def register_asset_action(self, asset_type: str, name: str, content: bytes, is_file: bool = True) -> Tuple[bool, str]:
        # TR: Mobil dosya yükleme veya domain kaydetme aksiyonu.
        # EN: Mobile file upload or domain registration action.
        if not self.active_user_pub_key:
            return False, self.L['not_logged_in']

        storage_size = len(content)
        keywords = ""
        if asset_type == 'domain':
            # Domain içeriği metin olmalı
            content_str = content.decode('utf-8', errors='ignore')
            keywords = extract_keywords(content_str)
            content = content_str # DB'ye string olarak kaydetmek için
            
        return self.asset_mgr.register_asset(self.active_user_pub_key, asset_type, name, content, storage_size, keywords)

    def mine_action(self) -> Dict[str, Any]:
        # TR: Madencilik denemesi
        # EN: Mining attempt.
        if not self.active_user_pub_key:
            return {'success': False, 'message': self.L['not_logged_in']}
            
        try:
            # ghost_server.py'deki mining mantığı (ödül hesaplama, limit kontrolü) korunur.
            reward, new_block = self.chain_mgr.mine_for_user(self.active_user_pub_key)

            if reward == 0.0:
                 return {'success': False, 'message': "Madencilik ödülü 0'a ulaştı. Yeni GHOST coin basılamaz."}
            
            # Başarılı ise
            if new_block:
                block_hash = new_block['hash']
                message = self.L['mine_message'].replace('{{ block_hash }}', block_hash[:10] + '...').replace('{{ reward }}', f"{reward:.4f}")
                return {'success': True, 'message': message}
            else:
                 # Hata mesajını (örn. 24 saat kuralı) BlockchainManager'dan al
                 return {'success': False, 'message': "Madencilik başarısız (limit veya zincir hatası)."}
        except Exception as e:
            return {'success': False, 'message': f"Madencilik Hatası: {e}"}

    def sync_from_backbone(self) -> Tuple[bool, str]:
        # TR: Merkezi sunucudan (Backbone) en son blok zincirini çeker.
        # EN: Pulls the latest blockchain from the central server (Backbone).
        for server_url in self.servers:
            try:
                # 1. Sunucunun zincirini çek
                response = requests.get(f"{server_url}/chain", timeout=10)
                if response.status_code == 200:
                    server_chain_data = response.json()
                    server_chain = server_chain_data.get('chain', [])
                    
                    if not server_chain: continue

                    # 2. Zinciri değiştirme mekanizması (resolve_conflicts)
                    current_length = self.chain_mgr.get_chain_length()
                    if len(server_chain) > current_length:
                        # TR: Sunucu zinciri daha uzun, yerel zinciri güncelle.
                        # EN: Server chain is longer, update local chain.
                        if self.chain_mgr.replace_chain(server_chain):
                            return True, f"{self.L['sync_success']} {len(server_chain)}"
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Sync failed with {server_url}: {e}")
                continue
        
        return False, "Sync failed: No active backbone server found or local chain is up to date."

    def set_language(self, lang_code: str):
        # TR: Kullanıcının dil tercihini ayarlar.
        # EN: Sets the user's language preference.
        if lang_code in LANGUAGES:
            self.lang_code = lang_code
            self.L = LANGUAGES[lang_code]
            self.db.set_config('lang', lang_code)
            return True
        return False

# --- KÜÇÜK NOT: BU KOD BLOKLARI SADECE MANTIĞI GÖSTERİR ---
# TR: Gerçek mobil uygulamada, bu MobileBackend sınıfı BeeWare/Toga veya Kivy 
# EN: In a real mobile app, this MobileBackend class would be instantiated by the Toga or Kivy 
# TR: arayüzü tarafından başlatılacak ve etkileşim kurulacaktır.
# EN: UI and interacted with.
# if __name__ == '__main__':
#     backend = MobileBackend()
#     # print(backend.get_current_user_state())
#     # print(backend.mine_action())
#     # print(backend.sync_from_backbone())
