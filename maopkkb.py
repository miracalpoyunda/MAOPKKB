import os
import re
import sys
import dis
import marshal
import struct
import tempfile
import subprocess
import importlib.util
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_NAME = "MAOPKKB"
VERSION = "1.0"

# Python bytecode için mevcut Python sürümünün magic number'ı.
CURRENT_MAGIC = importlib.util.MAGIC_NUMBER

# Çok büyük EXE'lerde aramayı sınırlamak için makul bir değer.
MAX_SCAN_SIZE = 512 * 1024 * 1024


def safe_decode(data: bytes) -> str:
    """
    EXE içinden bulunan metinleri güvenli biçimde metne dönüştürür.
    """
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_strings(data: bytes, minimum_length: int = 4):
    """
    Binary içerisindeki okunabilir ASCII / UTF-8 benzeri dizileri bulur.
    """
    pattern = re.compile(rb"[\x20-\x7e]{%d,}" % minimum_length)
    return [m.group().decode("ascii", errors="ignore") for m in pattern.finditer(data)]


def unique_keep_order(items):
    """
    Tekrarlı elemanları kaldırır, sıralamayı korur.
    """
    result = []
    seen = set()

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def looks_like_python_filename(name: str) -> bool:
    """
    Bir metnin Python dosya/modül adı gibi görünüp görünmediğini kontrol eder.
    """
    lower = name.lower()

    if lower.endswith(".py"):
        return True

    if lower.endswith(".pyc"):
        return True

    if "/" in name or "\\" in name:
        base = os.path.basename(name)
        if base.lower().endswith((".py", ".pyc")):
            return True

    return False


def normalize_python_name(name: str) -> str:
    """
    Bulunan dosya yolunu sade bir görüntüleme adına dönüştürür.
    """
    name = name.replace("\\", "/").strip()
    name = name.strip('"')

    while name.startswith("./"):
        name = name[2:]

    return name


def detect_python_version(data: bytes):
    """
    EXE içerisinde python3XX.dll / python3.x benzeri izleri arar.
    """
    text = safe_decode(data[: min(len(data), MAX_SCAN_SIZE)])

    patterns = [
        re.compile(r"python(3)(\d{1,2})\.dll", re.IGNORECASE),
        re.compile(r"python(3)(\d{1,2})", re.IGNORECASE),
        re.compile(r"python\s*3\.(\d{1,2})", re.IGNORECASE),
    ]

    candidates = []

    for pattern in patterns:
        for match in pattern.finditer(text):
            groups = match.groups()

            if len(groups) == 2:
                major = groups[0]
                minor = groups[1]
                candidates.append(f"{major}.{minor}")

            elif len(groups) == 1:
                candidates.append(f"3.{groups[0]}")

    candidates = unique_keep_order(candidates)

    if candidates:
        return candidates[0]

    return None


def detect_pyinstaller(data: bytes, strings):
    """
    PyInstaller'a özgü veya kuvvetli şekilde ilişkili metin izlerini arar.
    """
    lower_data = data.lower()

    strong_markers = [
        b"pyi_rth_",
        b"pyiboot01_bootstrap",
        b"pyinstaller",
        b"_meipass",
        b"pyz-00.pyz",
        b"pyz-00.pyz_extracted",
        b"pyi-windows-manifest-filename",
    ]

    found = []

    for marker in strong_markers:
        if marker.lower() in lower_data:
            found.append(marker.decode("ascii", errors="ignore"))

    string_markers = [
        "_MEIPASS",
        "PYZ-00.pyz",
        "pyiboot01_bootstrap",
        "pyi_rth_",
        "PyInstaller",
    ]

    for s in strings:
        for marker in string_markers:
            if marker.lower() in s.lower():
                found.append(s)

    found = unique_keep_order(found)

    return len(found) > 0, found


def find_python_files(strings):
    """
    Binary içerisindeki görünen .py / .pyc isimlerini bulur.
    """
    result = []

    for item in strings:
        normalized = normalize_python_name(item)

        if looks_like_python_filename(normalized):
            result.append(normalized)

    # Çok uzun ve anlamsız stringleri temizle.
    cleaned = []

    for item in result:
        if len(item) <= 240:
            cleaned.append(item)

    return unique_keep_order(cleaned)


def find_python_module_names(strings):
    """
    Bazı Python modül isimlerini ve paket izlerini bulmaya çalışır.
    """
    result = []

    known_modules = {
        "tkinter",
        "os",
        "sys",
        "json",
        "time",
        "random",
        "math",
        "re",
        "pathlib",
        "subprocess",
        "requests",
        "numpy",
        "pygame",
        "pyautogui",
        "PIL",
        "flask",
        "selenium",
        "urllib",
        "socket",
        "sqlite3",
        "threading",
        "asyncio",
        "logging",
        "ctypes",
        "hashlib",
        "base64",
        "zipfile",
        "marshal",
    }

    lowered = "\n".join(strings).lower()

    for module in sorted(known_modules):
        if module.lower() in lowered:
            result.append(module)

    return result


def scan_for_pyc(data: bytes, max_candidates: int = 50):
    """
    Mevcut Python sürümünün .pyc magic number'ını binary içerisinde arar.
    Gerçek bir code object bulunursa dis ile gösterilebilecek aday oluşturur.

    Not:
    PyInstaller çoğu zaman bytecode'u kendi PYZ arşiv yapısında sıkıştırdığı
    için bu yöntem her EXE'de sonuç vermeyebilir.
    """
    candidates = []

    start = 0

    while True:
        index = data.find(CURRENT_MAGIC, start)

        if index == -1:
            break

        start = index + 1

        # Standart pyc başlığı için en az 16 byte gerekir.
        if index + 16 >= len(data):
            continue

        # CPython 3.7+ için yaygın header uzunluğu 16 byte'tır.
        code_offset = index + 16

        try:
            code_object = marshal.loads(data[code_offset:])

            if isinstance(code_object, type((lambda: None).__code__)):
                candidates.append(
                    {
                        "offset": index,
                        "code": code_object,
                    }
                )

                if len(candidates) >= max_candidates:
                    break

        except Exception:
            continue

    return candidates


def make_bytecode_text(code_object):
    """
    Code object'i çalıştırmadan dis modülü ile bytecode çıktısı üretir.
    """
    output = []

    def add_code(code, indent=0, name=""):
        prefix = " " * indent

        if name:
            output.append(f"{prefix}# Kod nesnesi: {name}")

        output.append(f"{prefix}# Bytecode:")
        output.append("")

        try:
            bytecode_lines = []

            for instruction in dis.Bytecode(code):
                line = (
                    f"{instruction.offset:>5} "
                    f"{instruction.opname:<30} "
                    f"{str(instruction.argrepr)}"
                )

                bytecode_lines.append(prefix + line)

            output.extend(bytecode_lines)

        except Exception as exc:
            output.append(prefix + f"# Bytecode görüntülenemedi: {exc}")

        output.append("")

        # İç içe fonksiyonların code object'lerini bul.
        try:
            for const in code.co_consts:
                if isinstance(const, type(code)):
                    add_code(
                        const,
                        indent=indent + 4,
                        name=const.co_name,
                    )
        except Exception:
            pass

    add_code(code_object, name=getattr(code_object, "co_name", "<module>"))

    return "\n".join(output)


def try_decompile_pyc(code_object):
    """
    Harici bir decompiler kurulmuşsa kullanmayı dener.

    Öncelik:
    1) decompyle3
    2) uncompyle6

    Bu işlem seçilen EXE'yi çalıştırmaz.
    Sadece geçici bir .pyc dosyası oluşturup decompiler aracına verir.
    """
    temp_path = None

    try:
        pyc_bytes = (
            CURRENT_MAGIC
            + b"\x00\x00\x00\x00"
            + b"\x00" * 8
            + marshal.dumps(code_object)
        )

        fd, temp_path = tempfile.mkstemp(suffix=".pyc")
        os.close(fd)

        with open(temp_path, "wb") as f:
            f.write(pyc_bytes)

        commands = [
            [sys.executable, "-m", "decompyle3", temp_path],
            [sys.executable, "-m", "uncompyle6", temp_path],
        ]

        for command in commands:
            try:
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )

                if process.returncode == 0 and process.stdout.strip():
                    return process.stdout.strip()

            except Exception:
                continue

    except Exception:
        return None

    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return None


class Analyzer:
    def __init__(self):
        self.path = None
        self.data = b""
        self.strings = []
        self.python_files = []
        self.python_modules = []
        self.pyc_candidates = []

        self.is_python = False
        self.is_pyinstaller = False
        self.python_version = None
        self.pyinstaller_markers = []

    def analyze_file(self, path):
        """
        Seçilen EXE üzerinde yalnızca statik okuma yapar.
        EXE'yi çalıştırmaz.
        """
        self.path = path

        file_size = os.path.getsize(path)

        if file_size > MAX_SCAN_SIZE:
            with open(path, "rb") as f:
                self.data = f.read(MAX_SCAN_SIZE)
        else:
            with open(path, "rb") as f:
                self.data = f.read()

        self.strings = extract_strings(self.data)

        self.python_files = find_python_files(self.strings)
        self.python_modules = find_python_module_names(self.strings)

        self.python_version = detect_python_version(self.data)

        (
            self.is_pyinstaller,
            self.pyinstaller_markers,
        ) = detect_pyinstaller(self.data, self.strings)

        self.pyc_candidates = scan_for_pyc(self.data)

        python_indicators = 0

        lower_data = self.data.lower()

        indicators = [
            b"python",
            b"pyinstaller",
            b"_meipass",
            b"pyiboot",
            b"pyz-00.pyz",
            b"pyc",
        ]

        for indicator in indicators:
            if indicator in lower_data:
                python_indicators += 1

        if self.python_files:
            python_indicators += 2

        if self.pyc_candidates:
            python_indicators += 3

        if self.python_version:
            python_indicators += 2

        self.is_python = python_indicators >= 2

        return self.get_summary()

    def get_summary(self):
        return {
            "is_python": self.is_python,
            "pyinstaller": self.is_pyinstaller,
            "python_version": self.python_version,
            "python_files": self.python_files,
            "python_modules": self.python_modules,
            "pyc_count": len(self.pyc_candidates),
        }

    def get_file_names_for_ui(self):
        """
        Sol panelde gösterilecek Python dosyalarını oluşturur.
        """
        names = []

        for item in self.python_files:
            if item.lower().endswith(".pyc"):
                display = item
            elif item.lower().endswith(".py"):
                display = item
            else:
                continue

            names.append(display)

        # Gerçek bir dosya adı bulunamazsa bytecode adayları göster.
        if not names and self.pyc_candidates:
            for index in range(len(self.pyc_candidates)):
                names.append(f"bytecode_{index + 1}.pyc")

        return unique_keep_order(names)

    def get_code_for_name(self, name):
        """
        Seçilen Python dosyası / bytecode için mümkün olan kodu üretir.
        """
        for candidate in self.pyc_candidates:
            code_object = candidate["code"]

            if name.startswith("bytecode_"):
                decompiled = try_decompile_pyc(code_object)

                if decompiled:
                    return (
                        "Harici decompiler kullanılarak okunabilir kod elde edildi.\n\n"
                        + decompiled
                    )

                return (
                    "Kaynak kod birebir bulunamadı.\n"
                    "Python bytecode bulundu.\n"
                    "Okunabilir koda dönüştürme deneniyor.\n\n"
                    "Bu temel sürümde bytecode analizi gösteriliyor:\n\n"
                    + make_bytecode_text(code_object)
                )

        # EXE içerisinde .py adını bulduysak fakat içerik çıkarılamadıysa.
        return (
            "Dosya adı bulundu ancak bu temel sürümde içerik "
            "doğrudan çıkarılamadı.\n\n"
            "Kaynak kod birebir bulunamadı veya paket içerisinde "
            "erişilebilir biçimde yer almıyor."
        )


class MAOPKKBApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MAOPKKB")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        self.analyzer = Analyzer()

        self.selected_file = ""
        self.current_code = ""

        self.build_ui()

    def build_ui(self):
        title = tk.Label(
            self.root,
            text="MAOPKKB",
            font=("Segoe UI", 22, "bold"),
        )
        title.pack(pady=(15, 5))

        subtitle = tk.Label(
            self.root,
            text="Python EXE Statik Analiz Aracı",
            font=("Segoe UI", 10),
        )
        subtitle.pack(pady=(0, 10))

        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=15, pady=5)

        select_button = tk.Button(
            top_frame,
            text="EXE DOSYASI SEÇ",
            font=("Segoe UI", 10, "bold"),
            command=self.select_exe,
            padx=12,
            pady=7,
        )
        select_button.pack(side="left")

        save_button = tk.Button(
            top_frame,
            text="KAYDET",
            command=self.save_result,
            padx=12,
            pady=7,
        )
        save_button.pack(side="left", padx=8)

        copy_button = tk.Button(
            top_frame,
            text="KODU KOPYALA",
            command=self.copy_code,
            padx=12,
            pady=7,
        )
        copy_button.pack(side="left")

        security_label = tk.Label(
            top_frame,
            text="  Güvenlik: Seçilen EXE çalıştırılmaz.",
            font=("Segoe UI", 9, "bold"),
        )
        security_label.pack(side="right")

        info_frame = tk.LabelFrame(
            self.root,
            text="Analiz Bilgileri",
            padx=10,
            pady=10,
        )
        info_frame.pack(fill="x", padx=15, pady=10)

        self.file_label = tk.Label(
            info_frame,
            text="Seçilen dosya: -",
            anchor="w",
            justify="left",
        )
        self.file_label.pack(fill="x")

        self.tech_label = tk.Label(
            info_frame,
            text="Algılanan teknoloji: -",
            anchor="w",
            justify="left",
        )
        self.tech_label.pack(fill="x")

        self.pyinstaller_label = tk.Label(
            info_frame,
            text="PyInstaller: -",
            anchor="w",
            justify="left",
        )
        self.pyinstaller_label.pack(fill="x")

        self.version_label = tk.Label(
            info_frame,
            text="Python sürümü: Bulunamadı",
            anchor="w",
            justify="left",
        )
        self.version_label.pack(fill="x")

        self.status_label = tk.Label(
            info_frame,
            text="Durum: Hazır",
            anchor="w",
            justify="left",
        )
        self.status_label.pack(fill="x")

        main_frame = tk.Frame(self.root)
        main_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15),
        )

        left_frame = tk.LabelFrame(
            main_frame,
            text="Bulunan dosyalar",
            padx=5,
            pady=5,
        )
        left_frame.pack(
            side="left",
            fill="y",
            padx=(0, 8),
        )

        self.file_list = tk.Listbox(
            left_frame,
            width=34,
            font=("Consolas", 10),
            activestyle="dotbox",
        )
        self.file_list.pack(
            side="left",
            fill="y",
            expand=True,
        )

        list_scroll = ttk.Scrollbar(
            left_frame,
            orient="vertical",
            command=self.file_list.yview,
        )
        list_scroll.pack(side="right", fill="y")

        self.file_list.configure(
            yscrollcommand=list_scroll.set
        )
        self.file_list.bind(
            "<<ListboxSelect>>",
            self.file_selected,
        )

        right_frame = tk.LabelFrame(
            main_frame,
            text="Kod / Analiz Sonucu",
            padx=5,
            pady=5,
        )
        right_frame.pack(
            side="left",
            fill="both",
            expand=True,
        )

        self.code_text = tk.Text(
            right_frame,
            wrap="none",
            font=("Consolas", 10),
            undo=False,
        )
        self.code_text.pack(
            side="left",
            fill="both",
            expand=True,
        )

        y_scroll = ttk.Scrollbar(
            right_frame,
            orient="vertical",
            command=self.code_text.yview,
        )
        y_scroll.pack(side="right", fill="y")

        self.code_text.configure(
            yscrollcommand=y_scroll.set
        )

        x_scroll = ttk.Scrollbar(
            right_frame,
            orient="horizontal",
            command=self.code_text.xview,
        )
        x_scroll.pack(
            side="bottom",
            fill="x",
        )

        self.code_text.configure(
            xscrollcommand=x_scroll.set
        )

    def set_code(self, text):
        self.current_code = text

        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", text)

    def select_exe(self):
        path = filedialog.askopenfilename(
            title="Python EXE dosyası seç",
            filetypes=[
                ("EXE dosyaları", "*.exe"),
                ("Tüm dosyalar", "*.*"),
            ],
        )

        if not path:
            return

        self.selected_file = path

        self.file_label.config(
            text=f"Seçilen dosya: {path}"
        )

        self.status_label.config(
            text="Durum: Statik analiz yapılıyor..."
        )

        self.root.update_idletasks()

        try:
            summary = self.analyzer.analyze_file(path)
        except Exception as exc:
            messagebox.showerror(
                "MAOPKKB Hatası",
                f"Dosya analiz edilemedi:\n\n{exc}",
            )

            self.status_label.config(
                text="Durum: Analiz başarısız."
            )

            return

        if summary["is_python"]:
            technology = "Python"

            if summary["pyinstaller"]:
                technology += " + PyInstaller"

        else:
            technology = "Belirsiz / Python dışı olabilir"

        self.tech_label.config(
            text=f"Algılanan teknoloji: {technology}"
        )

        pyinstaller_text = (
            "Algılandı"
            if summary["pyinstaller"]
            else "Tespit edilemedi"
        )

        self.pyinstaller_label.config(
            text=f"PyInstaller: {pyinstaller_text}"
        )

        if summary["python_version"]:
            version_text = summary["python_version"]
        else:
            version_text = "Bulunamadı"

        self.version_label.config(
            text=f"Python sürümü: {version_text}"
        )

        self.file_list.delete(0, "end")

        file_names = self.analyzer.get_file_names_for_ui()

        for name in file_names:
            self.file_list.insert("end", name)

        modules = summary["python_modules"]

        result_lines = [
            "MAOPKKB ANALİZ SONUCU",
            "=" * 70,
            "",
            f"Dosya: {path}",
            "Çalıştırıldı mı: HAYIR",
            "Analiz yöntemi: STATİK",
            "",
        ]

        if summary["is_python"]:
            result_lines.append(
                "Python uygulaması olduğuna dair göstergeler bulundu."
            )
        else:
            result_lines.append(
                "Python uygulaması olduğu kesin olarak tespit edilemedi."
            )

        result_lines.append("")

        result_lines.append(
            "Not: Orijinal .py kaynak kodunun EXE'den birebir "
            "çıkarılması garanti edilemez."
        )

        result_lines.append(
            "Yorumlar, değişken isimleri ve başka kaynak kod bilgileri "
            "derleme sırasında kaybolmuş olabilir."
        )

        result_lines.append("")

        if modules:
            result_lines.append("Algılanan bazı Python modülleri:")

            for module in modules:
                result_lines.append(f" - {module}")

            result_lines.append("")

        if summary["pyc_count"] > 0:
            result_lines.append(
                f"Bulunan bytecode adayları: {summary['pyc_count']}"
            )

            result_lines.append(
                "Kaynak kod birebir bulunamadı."
            )

            result_lines.append(
                "Python bytecode bulundu."
            )

            result_lines.append(
                "Okunabilir koda dönüştürülmeye çalışılıyor."
            )

        self.set_code("\n".join(result_lines))

        if not summary["is_python"]:
            messagebox.showinfo(
                "MAOPKKB",
                "Python uygulaması olduğu kesin olarak tespit edilemedi.",
            )

        self.status_label.config(
            text=(
                "Durum: Analiz tamamlandı. "
                "Seçilen EXE çalıştırılmadı."
            )
        )

    def file_selected(self, event=None):
        selection = self.file_list.curselection()

        if not selection:
            return

        name = self.file_list.get(selection[0])

        code = self.analyzer.get_code_for_name(name)

        self.set_code(code)

    def save_result(self):
        content = self.code_text.get("1.0", "end-1c")

        if not content.strip():
            messagebox.showinfo(
                "MAOPKKB",
                "Kaydedilecek bir analiz sonucu yok.",
            )
            return

        path = filedialog.asksaveasfilename(
            title="Analiz sonucunu kaydet",
            defaultextension=".txt",
            filetypes=[
                ("Metin dosyası", "*.txt"),
                ("Tüm dosyalar", "*.*"),
            ],
        )

        if not path:
            return

        try:
            with open(
                path,
                "w",
                encoding="utf-8",
            ) as f:
                f.write(content)

            messagebox.showinfo(
                "MAOPKKB",
                "Analiz sonucu kaydedildi.",
            )

        except Exception as exc:
            messagebox.showerror(
                "MAOPKKB",
                f"Dosya kaydedilemedi:\n\n{exc}",
            )

    def copy_code(self):
        content = self.code_text.get(
            "1.0",
            "end-1c",
        )

        if not content.strip():
            messagebox.showinfo(
                "MAOPKKB",
                "Kopyalanacak kod yok.",
            )
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.root.update()

            messagebox.showinfo(
                "MAOPKKB",
                "Kod panoya kopyalandı.",
            )

        except Exception as exc:
            messagebox.showerror(
                "MAOPKKB",
                f"Kopyalama başarısız:\n\n{exc}",
            )


def main():
    root = tk.Tk()

    try:
        root.iconname(APP_NAME)
    except Exception:
        pass

    app = MAOPKKBApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()