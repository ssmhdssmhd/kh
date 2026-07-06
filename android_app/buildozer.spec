[app]

title = 工作助手
package.name = workassistant
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 3.0.0

requirements = python3,kivy,speechrecognition
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.0.0
fullscreen = 0

android.api = 33
android.ndk = 25b
android.sdk = 24
android.buildtools = 34.0.0
android.use_aapt2 = True
android.permissions = INTERNET,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.add_assets = data/
android.accept_sdk_license = True

android.build_mode = debug

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.add_libs_armeabi_v7a = 
android.add_libs_arm64_v8a = 
android.add_libs_x86 = 
android.add_libs_x86_64 =