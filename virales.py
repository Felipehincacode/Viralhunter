import customtkinter as ctk
import threading
import json
import os
import requests
import webbrowser
import time
import pandas as pd
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox
import google.generativeai as genai
from apify_client import ApifyClient

# ================= ESTÉTICA: CYBER-PREMIUM =================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# Paleta de Colores
C_BG = "#050505"          # Negro profundo
C_SIDEBAR = "#0F0F0F"     # Gris muy oscuro
C_CARD = "#1A1A1A"        # Tarjetas
C_ACCENT = "#00E676"      # Verde Neón
C_ACCENT_HOVER = "#00B359"
C_TEXT_MAIN = "#FFFFFF"
C_TEXT_SEC = "#808080"
C_INPUT_BG = "#2B2B2B"

# Tipografías
FONT_LOGO = ("Impact", 28)
FONT_H1 = ("Roboto Medium", 30)
FONT_H2 = ("Roboto Medium", 20)
FONT_BODY = ("Roboto", 14)
FONT_SMALL = ("Roboto", 12)

# ================= GESTOR DE DATOS =================
class ConfigManager:
    FILE = "viral_config.json"
    DEFAULTS = {
        "gemini_key": "",
        "apify_token": "",
        "first_run": True
    }

    def __init__(self):
        self.data = self.load()

    def load(self):
        if not os.path.exists(self.FILE): return self.DEFAULTS.copy()
        try:
            with open(self.FILE, "r") as f: return {**self.DEFAULTS, **json.load(f)}
        except: return self.DEFAULTS.copy()

    def save(self):
        with open(self.FILE, "w") as f: json.dump(self.data, f, indent=4)

    def update(self, key, val):
        self.data[key] = val
        self.save()

# ================= MOTOR VIRAL =================
class ViralEngine:
    def get_hooks(self, api_key, topic):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.0-flash')
            prompt = f"""
            Eres un experto en viralidad de TikTok. Tema: "{topic}".
            Genera 5 Search Queries (Hooks de búsqueda) para encontrar videos explosivos.
            Ej: "lo que nadie te dice de [tema]", "error fatal [tema]", "pov [tema]".
            OUTPUT: Solo las 5 frases separadas por comas.
            """
            resp = model.generate_content(prompt)
            return [x.strip() for x in resp.text.replace('\n','').split(',') if x.strip()][:5]
        except Exception as e: raise Exception(f"Error IA: {e}")

    def scrape(self, token, queries):
        client = ApifyClient(token)
        run = client.actor("clockworks/tiktok-scraper").call(run_input={
            "searchQueries": queries, "resultsPerPage": 10, "searchSection": "/video", "shouldDownloadCovers": False
        })
        if not run: raise Exception("Error conectando con Apify")
        return client.dataset(run["defaultDatasetId"]).list_items().items

    def process_data(self, raw, min_likes, months):
        clean = []
        limit = datetime.now() - timedelta(days=months*30)
        seen = set()
        
        for item in raw:
            try:
                vid_id = item.get('id')
                if vid_id in seen: continue
                
                stats = item.get('stats', {})
                likes = stats.get('diggCount') or item.get('diggCount', 0)
                ts = item.get('createTime')
                if not likes or not ts: continue
                
                likes = int(likes)
                dt = datetime.fromtimestamp(int(ts))
                
                if likes < min_likes or dt < limit: continue
                
                days = (datetime.now() - dt).days or 1
                velocity = likes / days 
                
                clean.append({
                    "title": item.get('text', 'Sin título'),
                    "url": item.get('webVideoUrl', f"https://tiktok.com/@u/video/{vid_id}"),
                    "likes": likes,
                    "velocity": velocity,
                    "date": dt.strftime("%d/%m/%Y"),
                    "author": item.get('authorMeta', {}).get('name', 'User')
                })
                seen.add(vid_id)
            except: continue
        
        return sorted(clean, key=lambda x: x['velocity'], reverse=True)

# ================= COMPONENTES UI =================
class CyberButton(ctk.CTkButton):
    def __init__(self, parent, text, command, **kwargs):
        kwargs.setdefault("fg_color", C_ACCENT)
        kwargs.setdefault("hover_color", C_ACCENT_HOVER)
        kwargs.setdefault("text_color", "black")
        kwargs.setdefault("font", ("Roboto", 15, "bold"))
        kwargs.setdefault("height", 50)
        kwargs.setdefault("corner_radius", 25)
        super().__init__(parent, text=text, command=command, **kwargs)

class CyberInput(ctk.CTkFrame):
    def __init__(self, parent, placeholder, icon_text="⚡", default=""):
        super().__init__(parent, fg_color=C_INPUT_BG, corner_radius=15, height=55)
        self.pack_propagate(False)
        ctk.CTkLabel(self, text=icon_text, font=("Segoe UI Emoji", 18)).pack(side="left", padx=(20, 10))
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder, fg_color="transparent", border_width=0,
                                  text_color="white", font=("Roboto", 16), placeholder_text_color=C_TEXT_SEC)
        self.entry.pack(side="left", fill="both", expand=True, padx=(0, 20))
        if default: self.entry.insert(0, default)
    def get(self): return self.entry.get()

class CyberSlider(ctk.CTkFrame):
    """Slider personalizado con display de valor en tiempo real"""
    def __init__(self, parent, label_text, from_val, to_val, start_val, suffix=""):
        super().__init__(parent, fg_color="transparent")
        self.suffix = suffix
        
        # Header (Texto Izq, Valor Der)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(header, text=label_text, font=("Roboto", 12, "bold"), text_color=C_TEXT_SEC).pack(side="left")
        self.val_label = ctk.CTkLabel(header, text=f"{int(start_val)}{suffix}", font=("Roboto", 12, "bold"), text_color=C_ACCENT)
        self.val_label.pack(side="right")
        
        # Slider
        self.slider = ctk.CTkSlider(self, from_=from_val, to=to_val, number_of_steps=100,
                                    button_color=C_ACCENT, button_hover_color=C_ACCENT_HOVER,
                                    progress_color=C_ACCENT, fg_color="#333",
                                    command=self.update_label)
        self.slider.pack(fill="x")
        self.slider.set(start_val)
        
    def update_label(self, value):
        val = int(value)
        # Formato K para likes (ej: 10500 -> 10.5K)
        if self.suffix == " Likes" and val >= 1000:
            txt = f"{val/1000:.1f}K{self.suffix}"
        else:
            txt = f"{val}{self.suffix}"
        self.val_label.configure(text=txt)

    def get(self):
        return int(self.slider.get())

class StatCard(ctk.CTkFrame):
    def __init__(self, parent, data):
        super().__init__(parent, fg_color=C_CARD, corner_radius=15)
        self.pack(fill="x", pady=8, padx=10)
        self.grid_columnconfigure(1, weight=1)
        
        thumb = ctk.CTkFrame(self, width=60, height=60, fg_color="#111", corner_radius=10)
        thumb.grid(row=0, column=0, rowspan=2, padx=15, pady=15)
        ctk.CTkLabel(thumb, text="▶", text_color=C_ACCENT, font=("Arial", 20)).place(relx=0.5, rely=0.5, anchor="center")
        
        t = data['title'][:60] + "..." if len(data['title']) > 60 else data['title']
        ctk.CTkLabel(self, text=t, font=("Roboto", 14, "bold"), text_color="white", anchor="w").grid(row=0, column=1, sticky="ew", pady=(15, 0))
        
        stats = f"🔥 {int(data['velocity'])}/día   |   ❤️ {data['likes']:,}   |   📅 {data['date']}"
        ctk.CTkLabel(self, text=stats, font=("Roboto", 12), text_color=C_ACCENT, anchor="w").grid(row=1, column=1, sticky="nw", pady=(2, 15))
        
        ctk.CTkButton(self, text="Ver ↗", width=60, fg_color="#333", hover_color="#444", 
                      command=lambda: webbrowser.open(data['url'])).grid(row=0, column=2, rowspan=2, padx=20)

# ================= APP PRINCIPAL =================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Viral Hunter Pro")
        self.geometry("1200x850") # Un poco más alto para los sliders
        self.configure(fg_color=C_BG)
        
        self.config = ConfigManager()
        self.engine = ViralEngine()
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.create_sidebar()
        self.create_main_area()
        
        self.views = {}
        self.setup_dashboard()
        self.setup_results()
        self.setup_settings()
        
        if self.config.data["first_run"]:
            self.show_view("settings")
            messagebox.showinfo("Bienvenido", "Por favor, configura tus API Keys para empezar.")
            self.config.update("first_run", False)
        else:
            self.show_view("dashboard")

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, fg_color=C_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="VIRAL\nHUNTER", font=FONT_LOGO, text_color=C_ACCENT).pack(pady=50)
        
        self.nav_btns = {}
        self.add_nav_btn("🚀  Scanner", "dashboard")
        self.add_nav_btn("📂  Resultados", "results")
        self.add_nav_btn("⚙️  Ajustes", "settings")

        ctk.CTkLabel(self.sidebar, text="v4.1 Pro", text_color=C_TEXT_SEC, font=FONT_SMALL).pack(side="bottom", pady=20)

    def add_nav_btn(self, text, view):
        btn = ctk.CTkButton(self.sidebar, text=text, anchor="w", fg_color="transparent", hover_color="#222", 
                            font=("Roboto", 14, "bold"), height=50, command=lambda: self.show_view(view))
        btn.pack(fill="x", padx=20, pady=5)
        self.nav_btns[view] = btn

    def create_main_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    # --- VISTAS ---
    def setup_dashboard(self):
        self.views["dashboard"] = ctk.CTkFrame(self.main_container, fg_color="transparent")
        v = self.views["dashboard"]
        
        # Caja Central
        center_box = ctk.CTkFrame(v, fg_color="transparent")
        center_box.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7)
        
        ctk.CTkLabel(center_box, text="Centro de Rastreo Viral", font=FONT_H1, text_color="white").pack(pady=(0, 5))
        ctk.CTkLabel(center_box, text="Define tu nicho y ajusta la sensibilidad.", font=FONT_BODY, text_color=C_TEXT_SEC).pack(pady=(0, 30))
        
        # 1. Input Tema
        self.input_topic = CyberInput(center_box, "Nicho (ej. Fitness en casa, IA Tools...)")
        self.input_topic.pack(fill="x", pady=(0, 20))
        
        # 2. Sliders Container (Lado a Lado)
        sliders_frame = ctk.CTkFrame(center_box, fg_color="transparent")
        sliders_frame.pack(fill="x", pady=(0, 30))
        
        # Slider Likes
        f1 = ctk.CTkFrame(sliders_frame, fg_color="transparent")
        f1.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.slider_likes = CyberSlider(f1, "MÍNIMO LIKES", 1000, 200000, 10000, " Likes")
        self.slider_likes.pack(fill="x")
        
        # Slider Tiempo
        f2 = ctk.CTkFrame(sliders_frame, fg_color="transparent")
        f2.pack(side="right", fill="x", expand=True, padx=(15, 0))
        self.slider_months = CyberSlider(f2, "ANTIGÜEDAD MÁXIMA", 1, 12, 3, " Meses")
        self.slider_months.pack(fill="x")
        
        # 3. Botón
        self.btn_run = CyberButton(center_box, "INICIAR ESCANEO", self.start_scan)
        self.btn_run.pack(fill="x")
        
        # Logs
        self.status_lbl = ctk.CTkLabel(center_box, text="Sistema Listo.", text_color=C_TEXT_SEC)
        self.status_lbl.pack(pady=(20, 0))
        
        self.progress = ctk.CTkProgressBar(center_box, height=4, progress_color=C_ACCENT, fg_color="#333")
        self.progress.pack(fill="x", pady=10)
        self.progress.set(0)

    def setup_results(self):
        self.views["results"] = ctk.CTkFrame(self.main_container, fg_color="transparent")
        v = self.views["results"]
        
        h = ctk.CTkFrame(v, fg_color="transparent")
        h.pack(fill="x", pady=(0, 20))
        
        self.lbl_res_count = ctk.CTkLabel(h, text="Resultados: 0", font=FONT_H1)
        self.lbl_res_count.pack(side="left")
        ctk.CTkButton(h, text="Exportar Excel", fg_color="#222", hover_color="#333", command=self.export_excel).pack(side="right")
        
        self.scroll_res = ctk.CTkScrollableFrame(v, fg_color="transparent")
        self.scroll_res.pack(fill="both", expand=True)

    def setup_settings(self):
        self.views["settings"] = ctk.CTkFrame(self.main_container, fg_color="transparent")
        v = self.views["settings"]
        
        box = ctk.CTkFrame(v, fg_color=C_CARD, corner_radius=20)
        box.place(relx=0.5, rely=0.4, anchor="center", relwidth=0.6)
        
        ctk.CTkLabel(box, text="Configuración API", font=FONT_H2).pack(pady=30)
        
        self.set_gemini = CyberInput(box, "Gemini API Key", "🧠", self.config.data["gemini_key"])
        self.set_gemini.pack(fill="x", padx=40, pady=10)
        
        self.set_apify = CyberInput(box, "Apify Token", "🕵️", self.config.data["apify_token"])
        self.set_apify.pack(fill="x", padx=40, pady=10)
        
        CyberButton(box, "GUARDAR CREDENCIALES", self.save_settings, height=40).pack(fill="x", padx=40, pady=40)

    # --- LÓGICA ---
    def show_view(self, name):
        for k, v in self.views.items(): v.pack_forget()
        self.views[name].pack(fill="both", expand=True)
        for k, btn in self.nav_btns.items():
            btn.configure(fg_color=C_ACCENT if k == name else "transparent", 
                          text_color="black" if k == name else "white")

    def log(self, text, progress_val=None):
        self.status_lbl.configure(text=text)
        if progress_val is not None:
            if progress_val == -1:
                self.progress.configure(mode="indeterminate")
                self.progress.start()
            else:
                self.progress.configure(mode="determinate")
                self.progress.stop()
                self.progress.set(progress_val)

    def start_scan(self):
        topic = self.input_topic.get()
        if not topic: return messagebox.showwarning("!", "Falta el tema.")
        
        self.btn_run.configure(state="disabled", text="ESCANNEANDO...")
        
        # Obtener valores de los sliders del HOME
        likes = self.slider_likes.get()
        months = self.slider_months.get()
        
        threading.Thread(target=self.worker, args=(topic, likes, months), daemon=True).start()

    def worker(self, topic, likes, months):
        try:
            self.log(f"Analizando '{topic}' (Filtro: {likes} likes, {months} meses)...", -1)
            queries = self.engine.get_hooks(self.config.data["gemini_key"], topic)
            
            self.log("Scrapeando TikTok...", -1)
            raw = self.engine.scrape(self.config.data["apify_token"], queries)
            
            self.log("Filtrando...", 0.8)
            data = self.engine.process_data(raw, likes, months)
            
            self.results_data = data
            self.after(0, self.finish_worker)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.log("Error.", 0))
        finally:
            self.after(0, lambda: self.btn_run.configure(state="normal", text="INICIAR ESCANEO"))

    def finish_worker(self):
        self.log(f"¡Listo! {len(self.results_data)} videos.", 1)
        for w in self.scroll_res.winfo_children(): w.destroy()
        self.lbl_res_count.configure(text=f"Resultados: {len(self.results_data)}")
        
        if not self.results_data:
            ctk.CTkLabel(self.scroll_res, text="Sin resultados.", font=FONT_H1).pack(pady=50)
        else:
            for vid in self.results_data:
                StatCard(self.scroll_res, vid)
        self.show_view("results")

    def save_settings(self):
        self.config.update("gemini_key", self.set_gemini.get())
        self.config.update("apify_token", self.set_apify.get())
        messagebox.showinfo("OK", "Keys Guardadas.")

    def export_excel(self):
        if hasattr(self, 'results_data') and self.results_data:
            f = filedialog.asksaveasfilename(defaultextension=".xlsx")
            if f: pd.DataFrame(self.results_data).to_excel(f, index=False)

if __name__ == "__main__":
    app = App()
    app.mainloop()