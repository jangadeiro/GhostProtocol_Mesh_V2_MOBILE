# 👻 Ghost Protocol - Mobile Mesh Network Application (Node) // Ghost Protocol - Mobil Mesh Ağı Uygulaması (Node)

**The Decentralized, Off-Grid Internet & Blockchain Layer**
*(Merkeziyetsiz, Şebekeden Bağımsız İnternet ve Blok Zinciri Katmanı)*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/Status-Beta-orange.svg)]()

---

# GhostProtocol Mobile Node 👻

**[TR]** Özgür, blokzincir tabanlı, sansürlenemez ve engellenemez bir internet yapısı.
**[EN]** A free, blockchain-based, uncensorable, and unstoppable internet infrastructure.

---

## 🌍 Proje Hakkında / About the Project

**[TR]**
GhostProtocol, merkeziyetsiz bir ağ (Mesh Network) ve blokzinciri teknolojisi kullanarak internet sansürlerini aşmayı hedefler. Bu mobil uygulama, cep telefonunuzu bir "Ghost Node" (Hayalet Düğüm) haline getirir. İnternet erişimi kısıtlansa bile, Bluetooth ve yerel ağlar üzerinden veriler yayılmaya devam eder.

**[EN]**
GhostProtocol aims to bypass internet censorship using a decentralized Mesh Network and blockchain technology. This mobile application turns your mobile phone into a "Ghost Node". Even if internet access is restricted, data continues to propagate via Bluetooth and local networks.

## 🚀 Özellikler / Features

##TR
* **Decentralized Web:** `.ghost` domain tescili, içerik barındırma ve gelişmiş arama özelliği.
* **Mobile Wallet:** GHOST coin transferi ve cüzdan yönetimi.
* **Unstoppable:** Merkezi sunucu yoktur, her telefon bir sunucudur.
* **Multi-Language:** Türkçe, English, Русский, Հայերեն.

##EN
* **Decentralized Web:** `.ghost` domain registration, content hosting, and advanced search capabilities.
* **Mobile Wallet:** GHOST coin transfer and wallet management.
* **Unstoppable:** No central server; each phone acts as a server.
* **Multi-Language:** Turkish, English, Russian, Armenian.

## 📱 Kurulum / Installation

### Android (APK)

##TR
1.  **Releases** kısmından en son `.apk` dosyasını indirin.
2.  Cihazınızda "Bilinmeyen Kaynaklar" iznini vererek yükleyin.
3.  Uygulamayı açın ve "Open Dashboard" butonuna tıklayın.

##EN
1. Download the latest `.apk` file from the **Releases** section.
2. Install it on your device by granting "Unknown Sources" permission.
3. Open the application and click the "Open Dashboard" button.

### iOS

##TR
1.  Bu repoyu klonlayın.
2.  `kivy-ios` kullanarak Xcode projesini derleyin.
3.  Cihazınıza yükleyin.

##EN
1. Clone this repository.
2. Compile the Xcode project using `kivy-ios`.
3. Install it on your device.

   
## 🛠️ Geliştirme / Development

Gereksinimler / Requirements: `python3`, `kivy`, `buildozer`

```bash
# Repoyu klonlayın / Clone the repo
git clone [https://github.com/jangadeiro/GhostProtocol_Mesh_V2_MOBILE.git](https://github.com/jangadeiro/GhostProtocol_Mesh_V2_MOBILE.git)
cd GhostProtocol_Mesh_V2_MOBILE

# Bağımlılıkları yükleyin / Install dependencies
pip install kivy flask requests

# Uygulamayı test edin / Test the app
python main.py
