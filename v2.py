import customtkinter as ctk
import threading
import json
import os
import requests
import webbrowser
import time
import math
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

# ================= FONDO: VANTA TRUNK (MATEMÁTICO) =================
class VantaTrunkEffect(ctk.CTkCanvas):
    def __init__(self, master, width, height, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, bg=C_BG, **kwargs)
        self.width = width
        self.height = height
        
        # Configuración del efecto
        self.spacing = 35       
        self.chaos = 25         
        self.color = "#002612"  
        
        self.time = 0
        self.speed = 0.05
        self.animate()

    def animate(self):
        self.delete("trunk_line") 
        step_y = 25 
        for x_base in range(0, self.width + self.spacing, self.spacing):
            coords = []
            for y in range(0, self.height + step_y, step_y):
                wave1 = math.sin((y * 0.008) + (x_base * 0.005) + self.time) * self.chaos
                wave2 = math.cos((y * 0.02) - self.time * 1.5) * (self.chaos * 0.4)
                x_final = x_base + wave1 + wave2
                coords.extend([x_final, y])
            self.create_line(coords, fill=self.color, width=2, smooth=True, tags="trunk_line")
        self.time += self.speed
        self.after(30, self.animate)

# ================= COMPONENTES UI =================
class CyberButton(ctk.CTkButton):
    def __init__(self, parent, text, command, **kwargs):
        kwargs.setdefault("fg_color", C_ACCENT)
        kwargs.setdefault("hover_color", C_ACCENT_HOVER)
        kwargs.setdefault("text_color", "black")
        kwargs.setdefault("font", ("Roboto", 15, "bold"))
        kwargs.setdefault("height", 50)
        kwargs.setdefault("corner_radius", 25)
        kwargs.setdefault("cursor", "hand2") 
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
    def __init__(self, parent, label_text, from_val, to_val, start_val, suffix=""):
        super().__init__(parent, fg_color="transparent")
        self.suffix = suffix
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(header, text=label_text, font=("Roboto", 12, "bold"), text_color=C_TEXT_SEC).pack(side="left")
        self.val_label = ctk.CTkLabel(header, text=f"{int(start_val)}{suffix}", font=("Roboto", 12, "bold"), text_color=C_ACCENT)
        self.val_label.pack(side="right")
        self.slider = ctk.CTkSlider(self, from_=from_val, to=to_val, number_of_steps=100,
                                    button_color=C_ACCENT, button_hover_color=C_ACCENT_HOVER,
                                    progress_color=C_ACCENT, fg_color="#333",
                                    command=self.update_label, cursor="hand2")
        self.slider.pack(fill="x")
        self.slider.set(start_val)
        
    def update_label(self, value):
        val = int(value)
        if self.suffix == " Likes" and val >= 1000: txt = f"{val/1000:.1f}K{self.suffix}"
        else: txt = f"{val}{self.suffix}"
        self.val_label.configure(text=txt)

    def get(self): return int(self.slider.get())

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
        
        ctk.CTkButton(self, text="Ver ↗", width=60, fg_color="#333", hover_color="#444", cursor="hand2",
                      command=lambda: webbrowser.open(data['url'])).grid(row=0, column=2, rowspan=2, padx=20)

# ================= WIZARD (ONBOARDING) =================
class OnboardingWizard(ctk.CTkFrame):
    def __init__(self, app, on_complete):
        super().__init__(app, fg_color=C_BG) # Tapa todo el fondo
        self.app = app
        self.on_complete = on_complete
        self.step = 0
        
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Caja Central del Wizard
        self.box = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=20, border_width=1, border_color="#333")
        self.box.place(relx=0.5, rely=0.5, anchor="center", width=600, height=550)
        self.box.pack_propagate(False)
        
        self.render_step()

    def render_step(self):
        for w in self.box.winfo_children(): w.destroy()
        
        # Datos de los pasos
        steps = [
            {
                "title": "VIRAL HUNTER",
                "icon": "🚀",
                "desc": "Bienvenido a la suite de inteligencia viral definitiva.\nConfigura tus motores para empezar.",
                "action": "COMENZAR"
            },
            {
                "title": "CEREBRO IA",
                "icon": "🧠",
                "desc": "Necesitamos una Key de Google Gemini para analizar tendencias.",
                "input_label": "Gemini API Key",
                "link": "https://aistudio.google.com/app/apikey",
                "action": "SIGUIENTE"
            },
            {
                "title": "MOTOR DE DATOS",
                "icon": "🕵️",
                "desc": "Necesitamos un Token de Apify para extraer datos de TikTok.",
                "input_label": "Apify Token",
                "link": "https://console.apify.com/",
                "action": "SIGUIENTE"
            },
            {
                "title": "DESARROLLADOR",
                "icon": "👨‍💻",
                "desc": "Herramienta creada con pasión.\n¡Conectemos en redes!",
                "socials": True,
                "action": "FINALIZAR"
            }
        ]
        
        data = steps[self.step]
        
        # UI
        ctk.CTkLabel(self.box, text=data["icon"], font=("Arial", 60)).pack(pady=(40, 10))
        ctk.CTkLabel(self.box, text=data["title"], font=FONT_H1, text_color="white").pack(pady=(0, 10))
        ctk.CTkLabel(self.box, text=data["desc"], font=FONT_BODY, text_color=C_TEXT_SEC).pack(pady=(0, 20))
        
        self.current_entry = None
        
        # Input Key (Pasos 1 y 2)
        if "input_label" in data:
            self.current_entry = CyberInput(self.box, data["input_label"], "🔑")
            self.current_entry.pack(fill="x", padx=50, pady=10)
            
            ctk.CTkButton(self.box, text="Conseguir Key Gratis ↗", fg_color="transparent", text_color=C_ACCENT,
                          hover_color="#222", cursor="hand2", font=("Roboto", 12),
                          command=lambda: webbrowser.open(data["link"])).pack()
                          
        # Redes Sociales (Paso 3)
        if "socials" in data:
            social_frame = ctk.CTkFrame(self.box, fg_color="transparent")
            social_frame.pack(fill="x", padx=60, pady=10)
            
            CyberButton(social_frame, "GitHub: @felipehincacode", 
                        command=lambda: webbrowser.open("https://github.com/felipehincacode"),
                        fg_color="#333", hover_color="#24292e", height=45).pack(fill="x", pady=5)
                        
            CyberButton(social_frame, "Instagram: @caracol.aventurero", 
                        command=lambda: webbrowser.open("https://instagram.com/caracol.aventurero"),
                        fg_color="#333", hover_color="#C13584", height=45).pack(fill="x", pady=5)

        # Botón Acción
        CyberButton(self.box, data["action"], self.next_step, width=200).pack(side="bottom", pady=40)

    def next_step(self):
        # Guardar keys
        if self.current_entry:
            val = self.current_entry.get().strip()
            if self.step == 1: self.app.config.update("gemini_key", val)
            if self.step == 2: self.app.config.update("apify_token", val)
            
        self.step += 1
        if self.step >= 4:
            self.app.config.update("first_run", False)
            self.destroy()
            self.on_complete() # Callback para mostrar dashboard
        else:
            self.render_step()

# ================= APP PRINCIPAL =================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Viral Hunter Pro")
        self.geometry("1200x850")
        self.configure(fg_color=C_BG)
        
        self.config = ConfigManager()
        self.engine = ViralEngine()
        
        # 1. CAPA DE FONDO (Vanta Trunk)
        self.bg_effect = VantaTrunkEffect(self, width=1200, height=850)
        self.bg_effect.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # 2. CAPA UI PRINCIPAL (Transparente)
        self.main_layer = ctk.CTkFrame(self, fg_color="transparent")
        self.main_layer.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.main_layer.grid_columnconfigure(1, weight=1)
        self.main_layer.grid_rowconfigure(0, weight=1)
        
        self.create_sidebar()
        self.create_main_area()
        
        self.views = {}
        self.setup_dashboard()
        self.setup_results()
        self.setup_settings()
        
        # LÓGICA DE INICIO: ¿Wizard o Dashboard?
        if self.config.data["first_run"]:
            # Lanzamos el wizard encima de todo
            OnboardingWizard(self, on_complete=lambda: self.show_view("dashboard"))
        else:
            self.show_view("dashboard")

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.main_layer, width=250, fg_color=C_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="VIRAL\nHUNTER", font=FONT_LOGO, text_color=C_ACCENT).pack(pady=50)
        
        self.nav_btns = {}
        self.add_nav_btn("🚀  Scanner", "dashboard")
        self.add_nav_btn("📂  Resultados", "results")
        self.add_nav_btn("⚙️  Ajustes", "settings")

        ctk.CTkLabel(self.sidebar, text="v6.0 Final", text_color=C_TEXT_SEC, font=FONT_SMALL).pack(side="bottom", pady=20)

    def add_nav_btn(self, text, view):
        btn = ctk.CTkButton(self.sidebar, text=text, anchor="w", fg_color="transparent", hover_color="#222", 
                            font=("Roboto", 14, "bold"), height=50, cursor="hand2", command=lambda: self.show_view(view))
        btn.pack(fill="x", padx=20, pady=5)
        self.nav_btns[view] = btn

    def create_main_area(self):
        self.main_container = ctk.CTkFrame(self.main_layer, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    # --- VISTAS ---
    def setup_dashboard(self):
        self.views["dashboard"] = ctk.CTkFrame(self.main_container, fg_color="transparent")
        v = self.views["dashboard"]
        
        center_box = ctk.CTkFrame(v, fg_color="#111111", border_width=1, border_color="#333", corner_radius=20)
        center_box.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7)
        
        ctk.CTkLabel(center_box, text="Centro de Rastreo Viral", font=FONT_H1, text_color="white").pack(pady=(30, 5))
        ctk.CTkLabel(center_box, text="Define tu nicho y ajusta la sensibilidad.", font=FONT_BODY, text_color=C_TEXT_SEC).pack(pady=(0, 30))
        
        self.input_topic = CyberInput(center_box, "Nicho (ej. Fitness en casa, IA Tools...)")
        self.input_topic.pack(fill="x", padx=30, pady=(0, 20))
        
        sliders_frame = ctk.CTkFrame(center_box, fg_color="transparent")
        sliders_frame.pack(fill="x", padx=30, pady=(0, 30))
        
        f1 = ctk.CTkFrame(sliders_frame, fg_color="transparent")
        f1.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.slider_likes = CyberSlider(f1, "MÍNIMO LIKES", 1000, 200000, 10000, " Likes")
        self.slider_likes.pack(fill="x")
        
        f2 = ctk.CTkFrame(sliders_frame, fg_color="transparent")
        f2.pack(side="right", fill="x", expand=True, padx=(15, 0))
        self.slider_months = CyberSlider(f2, "ANTIGÜEDAD MÁXIMA", 1, 12, 3, " Meses")
        self.slider_months.pack(fill="x")
        
        self.btn_run = CyberButton(center_box, "INICIAR ESCANEO", self.start_scan)
        self.btn_run.pack(fill="x", padx=30)
        
        self.status_lbl = ctk.CTkLabel(center_box, text="Sistema Listo.", text_color=C_TEXT_SEC)
        self.status_lbl.pack(pady=(20, 0))
        
        self.progress = ctk.CTkProgressBar(center_box, height=4, progress_color=C_ACCENT, fg_color="#333")
        self.progress.pack(fill="x", pady=(10, 30))
        self.progress.set(0)

    def setup_results(self):
        self.views["results"] = ctk.CTkFrame(self.main_container, fg_color="transparent")
        v = self.views["results"]
        
        h = ctk.CTkFrame(v, fg_color="transparent")
        h.pack(fill="x", pady=(0, 20))
        
        self.lbl_res_count = ctk.CTkLabel(h, text="Resultados: 0", font=FONT_H1)
        self.lbl_res_count.pack(side="left")
        ctk.CTkButton(h, text="Exportar Excel", fg_color="#222", hover_color="#333", cursor="hand2", command=self.export_excel).pack(side="right")
        
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
        self.configure(cursor="watch") # Cursor reloj
        
        likes = self.slider_likes.get()
        months = self.slider_months.get()
        
        threading.Thread(target=self.worker, args=(topic, likes, months), daemon=True).start()

    def worker(self, topic, likes, months):
        try:
            self.log(f"Analizando '{topic}'...", -1)
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
            self.after(0, lambda: self.configure(cursor="arrow"))

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