[app]

# (str) Title of your application
title = GhostProtocol Mobile

# (str) Package name
package.name = ghostmobile

# (str) Package domain (needed for android/ios packaging)
package.domain = org.ghostprotocol

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (str) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# TR: Flask ve istekler için gerekli kütüphaneler
# EN: Libraries required for Flask and requests
requirements = python3,kivy,flask,requests,jinja2,markupsafe,werkzeug

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivy = ../../kivy

# (list) Permissions
# TR: İnternet erişimi için gerekli izinler
# EN: Permissions required for internet access
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 31

# (int) Minimum API your APK will support.
android.minapi = 21

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Service to keep the node running in background (Optional but recommended for full node)
# services = ghost_service:ghost_service.py

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
