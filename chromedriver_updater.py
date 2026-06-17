import os
import shutil
import zipfile
import requests
from win32com.client import Dispatch
import platform
import ctypes
import sys

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def elevate_if_needed():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

def download_chromedriver(url, save_path):
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True, f"Dosya indirildi: {save_path}"
    else:
        return False, f"İndirme hatası. HTTP {response.status_code}"

def extract_zip(zip_path, extract_to):
    try:
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return True, f"ZIP çıkarıldı: {extract_to}"
    except Exception as e:
        return False, f"ZIP çıkarma hatası: {e}"

def get_version_via_com(filename):
    try:
        parser = Dispatch("Scripting.FileSystemObject")
        version = parser.GetFileVersion(filename)
        return version if version else None
    except Exception:
        return None

def find_chromedriver(start_path):
    chromedriver_paths = []
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if file.lower() == "chromedriver.exe":
                chromedriver_paths.append(os.path.join(root, file))
    return chromedriver_paths

def replace_chromedriver(old_paths, new_path):
    """Tüm eski chromedriver.exe dosyalarını yenisiyle değiştirir. Sonuçları liste olarak döner."""
    if not os.path.exists(new_path):
        return [f"HATA: Yeni dosya bulunamadı: {new_path}"]
    
    results = []
    for old_path in old_paths:
        try:
            shutil.copyfile(new_path, old_path)
            results.append(f"✔ Değiştirildi: {old_path}")
        except PermissionError:
            results.append(f"✘ Yetki hatası: {old_path}")
        except Exception as e:
            results.append(f"✘ Hata [{old_path}]: {e}")
    return results

def get_system_architecture():
    return platform.architecture()[0]

def show_messagebox(message, title="Chromedriver Güncelleme"):
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x1)

def main():
    elevate_if_needed()

    system_arch = get_system_architecture()

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    
    versions = list(filter(None, [get_version_via_com(p) for p in chrome_paths]))
    
    if not versions:
        show_messagebox("Chrome yüklü değil veya sürüm bilgisi alınamadı.")
        return

    version = versions[0]
    message = f"Chrome Sürümü: {version}\n"

    # Mimari bazlı URL ve klasör adı
    if system_arch == '32bit':
        arch_tag = "win32"
        extract_subfolder = "chromedriver-win32"
    else:
        arch_tag = "win64"
        extract_subfolder = "chromedriver-win64"

    url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/{arch_tag}/chromedriver-{arch_tag}.zip"
    message += f"İndirme URL: {url}\n\n"

    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    zip_save_path = os.path.join(desktop_path, "chromedriver.zip")
    extract_folder = os.path.join(desktop_path, "chromedriver_update")

    # İndir
    ok, result = download_chromedriver(url, zip_save_path)
    message += result + "\n"
    if not ok:
        show_messagebox(message)
        return

    # Çıkar
    ok, result = extract_zip(zip_save_path, extract_folder)
    message += result + "\n"
    if not ok:
        show_messagebox(message)
        return

    # Yeni chromedriver.exe yolu
    new_chromedriver_path = os.path.join(extract_folder, extract_subfolder, "chromedriver.exe")
    if not os.path.exists(new_chromedriver_path):
        message += f"HATA: Beklenen konumda chromedriver.exe bulunamadı:\n{new_chromedriver_path}\n"
        show_messagebox(message)
        return

    # Sistem genelinde ara ve değiştir
    message += "\nSistemde bulunan chromedriver.exe dosyaları:\n"
    found_paths = find_chromedriver(r"C:\\")

    if found_paths:
        for p in found_paths:
            message += f"  {p}\n"
        message += "\nGüncelleme sonuçları:\n"
        replace_results = replace_chromedriver(found_paths, new_chromedriver_path)
        message += "\n".join(replace_results) + "\n"
    else:
        message += "  Hiç chromedriver.exe bulunamadı.\n"

    # Geçici ZIP temizle
    try:
        os.remove(zip_save_path)
    except Exception:
        pass

    show_messagebox(message)
    print("İşlem tamamlandı.")

if __name__ == "__main__":
    main()
