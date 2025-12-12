# 👻 Ghost Protocol - Mobile Mesh Network Application (Node) // Ghost Protocol - Mobil Mesh Ağı Uygulaması (Node)

**The Decentralized, Off-Grid Internet & Blockchain Layer**
*(Merkeziyetsiz, Şebekeden Bağımsız İnternet ve Blok Zinciri Katmanı)*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/Status-Beta-orange.svg)]()

---

## 🌍 Language Selection / Dil Seçimi

- [🇹🇷 **Türkçe**](#-turkish)
- [🇬🇧 **English**](#-english)

---

<a name="-turkish">
## 🇹🇷 Türkçe</a>

Ghost Protocol, merkeziyetsiz bir ağ altyapısı üzerine kurulmuş, sansüre dayanıklı, şeffaf ve kullanıcı odaklı bir içerik platformudur. Bu depo, projenin mobil cihazlara (Android & iOS) uyarlanmış, hafif ve dış bağımlılıklardan arındırılmış **Ghost Mesh Node** uygulamasını içerir.

Bu uygulama, masaüstü/sunucu (Backbone) versiyonundan farklı olarak, mobil cihazların sınırlı kaynakları düşünülerek tasarlanmıştır.

### 🌟 Temel Özellikler

* **Mobil Dostu:** Flask, Jinja2 gibi web bağımlılıklarından arındırılmıştır.
* **Tam Blockchain İşlevselliği:** Yerel SQLite veritabanı ile blok zinciri, işlem ve bakiye yönetimi.
* **Varlık Kaydı:** Kullanıcıların .ghost domainlerini ve medya varlıklarını mobil cihazlarında barındırma ve kaydetme yeteneği.
* **Çoklu Dil Desteği:** TR, EN, RU, HY dilleri için tam arayüz çevirisi.
* **Merkezi Sunucu Senkronizasyonu (Backbone Sync):** Mobil cihaz, merkezi GhostProtocol Sunucusu'ndan (Backbone) en güncel blok zincirini çekebilir.

### 🛠️ Kurulum ve Geliştirme

Bu proje, Python tabanlı bir mobil uygulama oluşturma çerçevesi kullanılarak paketlenmelidir. Tavsiye edilen araçlar:

1.  **BeeWare (Toga & Briefcase):** Python kodunu native mobil uygulamalara dönüştürmek için en modern araç setidir.
2.  **Kivy:** Hızlı prototipleme ve çapraz platform desteği sunan popüler bir Python kütüphanesidir.

#### BeeWare ile Kurulum Adımları (Önerilen)

1.  **Gereksinimler:** Python 3.8+
2.  **Briefcase Kurulumu:** `pip install briefcase`
3.  **Proje Oluşturma:** `briefcase create` komutu ile projenizi BeeWare şablonuna göre yapılandırın. (Bu depodaki `ghost_protocol_mobile_app.py` dosyası, projenizin ana uygulama mantığını oluşturacaktır.)
4.  **Bağımlılıklar:** `cryptography`, `requests`, `sqlite3` (Python standart kütüphanesinde mevcuttur), `hashlib` (mevcut).
5.  **Derleme ve Paketleme:**
    * Android için: `briefcase build android`
    * iOS için: `briefcase build ios`

---
<a name="-english">
## 🇺🇸 English</a>

Ghost Protocol is a censorship-resistant, transparent, and user-centric content platform built on a decentralized network infrastructure. This repository contains the **Ghost Mesh Node** application, which is the lightweight, dependency-free mobile adaptation of the project for devices (Android & iOS).

Unlike the desktop/server (Backbone) version, this application is designed with the limited resources of mobile devices in mind.

### 🌟 Core Features

* **Mobile-Friendly:** Freed from web dependencies like Flask and Jinja2.
* **Full Blockchain Functionality:** Local SQLite database for blockchain, transaction, and balance management.
* **Asset Registration:** Ability for users to host and register their .ghost domains and media assets locally on their mobile device.
* **Multi-Language Support:** Complete UI translations for TR, EN, RU, and HY languages.
* **Backbone Server Synchronization:** The mobile device can pull the most up-to-date blockchain from the central GhostProtocol Server (Backbone).

### 🛠️ Installation and Development

This project must be packaged using a framework designed for creating Python-based mobile applications. Recommended tools include:

1.  **BeeWare (Toga & Briefcase):** The most modern toolset for turning Python code into native mobile apps.
2.  **Kivy:** A popular Python library offering rapid prototyping and cross-platform support.

#### Installation Steps with BeeWare (Recommended)

1.  **Prerequisites:** Python 3.8+
2.  **Briefcase Installation:** `pip install briefcase`
3.  **Project Setup:** Structure your project according to the BeeWare template using `briefcase create`. (The `ghost_protocol_mobile_app.py` file in this repository serves as the core application logic.)
4.  **Dependencies:** Ensure core dependencies like `cryptography`, `requests`, `sqlite3` (comes with Python), and `hashlib` (comes with Python) are handled in the mobile build process.
5.  **Build and Package:**
    * For Android: `briefcase build android`
    * For iOS: `briefcase build ios`
