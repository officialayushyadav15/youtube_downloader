import yt_dlp
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import subprocess
import shutil
import webbrowser
import json
from datetime import datetime

class YoutubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Downloader")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        # Check if ffmpeg is installed
        self.ffmpeg_installed = self.check_ffmpeg()
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 10))
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL input
        ttk.Label(self.main_frame, text="Enter YouTube URL:").grid(column=0, row=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(self.main_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(column=0, row=1, sticky=(tk.W, tk.E), pady=5)
        
        # Output directory
        ttk.Label(self.main_frame, text="Save Location:").grid(column=0, row=2, sticky=tk.W, pady=5)
        
        self.dir_frame = ttk.Frame(self.main_frame)
        self.dir_frame.grid(column=0, row=3, sticky=(tk.W, tk.E), pady=5)
        
        self.dir_var = tk.StringVar()
        # Set default directory to Downloads folder
        self.dir_var.set(os.path.join(os.path.expanduser("~"), "Downloads"))
        self.dir_entry = ttk.Entry(self.dir_frame, textvariable=self.dir_var, width=40)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.browse_btn = ttk.Button(self.dir_frame, text="Browse", command=self.browse_directory)
        self.browse_btn.pack(side=tk.RIGHT, padx=5)

        # Quality selection
        ttk.Label(self.main_frame, text="Video Quality:").grid(column=0, row=4, sticky=tk.W, pady=5)
        
        self.quality_frame = ttk.Frame(self.main_frame)
        self.quality_frame.grid(column=0, row=5, sticky=(tk.W, tk.E), pady=5)
        
        self.quality_var = tk.StringVar(value="best")
        
        qualities = [
            ("Best Quality", "best"),
            ("4K", "bestvideo[height<=2160]+bestaudio/best[height<=2160]"),
            ("1080p", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
            ("720p", "best[height<=720]"),
            ("480p", "best[height<=480]"),
            ("360p", "best[height<=360]"),
            ("Audio Only (MP3)", "bestaudio/best")
        ]
        
        self.quality_combobox = ttk.Combobox(self.quality_frame, 
                                            textvariable=self.quality_var,
                                            values=[q[0] for q in qualities],
                                            state="readonly")
        self.quality_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.quality_combobox.current(0)
        
        # FFmpeg status label (only show if not installed)
        if not self.ffmpeg_installed:
            self.ffmpeg_frame = ttk.Frame(self.main_frame)
            self.ffmpeg_frame.grid(column=0, row=6, sticky=(tk.W, tk.E), pady=2)
            
            self.ffmpeg_label = ttk.Label(
                self.ffmpeg_frame, 
                text="⚠️ FFmpeg not detected. 4K/1080p quality may not work correctly.", 
                foreground="red"
            )
            self.ffmpeg_label.pack(side=tk.LEFT)
            
            self.install_ffmpeg_btn = ttk.Button(
                self.ffmpeg_frame, 
                text="Install FFmpeg", 
                command=self.show_ffmpeg_instructions
            )
            self.install_ffmpeg_btn.pack(side=tk.RIGHT)
        
        # Map display names to format strings
        self.quality_map = {q[0]: q[1] for q in qualities}
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.main_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(column=0, row=7, sticky=(tk.W, tk.E), pady=10)
        
        # Status message
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.grid(column=0, row=8, sticky=tk.W, pady=5)
        
        # Button frame for multiple buttons
        self.btn_frame = ttk.Frame(self.main_frame)
        self.btn_frame.grid(column=0, row=9, sticky=tk.E, pady=10)
        
        # History button
        self.history_btn = ttk.Button(self.btn_frame, text="Download History", 
                                     command=self.show_download_history)
        self.history_btn.pack(side=tk.LEFT, padx=5)
        
        # Open folder button
        self.open_folder_btn = ttk.Button(self.btn_frame, text="Open Download Folder", 
                                         command=self.open_download_folder)
        self.open_folder_btn.pack(side=tk.LEFT, padx=5)
        
        # Download button
        self.download_btn = ttk.Button(self.btn_frame, text="Download", command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        self.main_frame.columnconfigure(0, weight=1)
        
        # Store downloaded file path
        self.downloaded_file_path = None
        
        # Load download history
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_history.json")
        self.download_history = self.load_download_history()
    
    def check_ffmpeg(self):
        """Check if ffmpeg is installed and available in the system PATH"""
        return shutil.which('ffmpeg') is not None
    
    def show_ffmpeg_instructions(self):
        """Display instructions for installing FFmpeg"""
        message = (
            "FFmpeg is required for downloading 4K and 1080p videos with separate video/audio tracks.\n\n"
            "To install FFmpeg:\n"
            "1. Download from the official website\n"
            "2. Add it to your system PATH\n\n"
            "Would you like to open the FFmpeg download page?"
        )
        if messagebox.askyesno("FFmpeg Required", message):
            webbrowser.open("https://ffmpeg.org/download.html")
    
    def load_download_history(self):
        """Load download history from JSON file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading history: {e}")
                return []
        return []
    
    def save_download_history(self):
        """Save download history to JSON file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.download_history, f, indent=4)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def add_to_history(self, url, title, filename, quality, size_mb):
        """Add a download to history"""
        entry = {
            "url": url,
            "title": title,
            "filename": filename,
            "quality": quality,
            "size_mb": size_mb,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.download_history.append(entry)
        self.save_download_history()
    
    def show_download_history(self):
        """Show download history in a new window"""
        if not self.download_history:
            messagebox.showinfo("Download History", "No download history available")
            return
            
        history_window = tk.Toplevel(self.root)
        history_window.title("Download History")
        history_window.geometry("800x400")
        
        # Create a frame with scrollbar
        frame = ttk.Frame(history_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview
        columns = ("date", "title", "quality", "size", "location")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        # Define headings
        tree.heading("date", text="Date")
        tree.heading("title", text="Title")
        tree.heading("quality", text="Quality")
        tree.heading("size", text="Size (MB)")
        tree.heading("location", text="File Location")
        
        # Define column widths
        tree.column("date", width=120, anchor="center")
        tree.column("title", width=250, anchor="w")
        tree.column("quality", width=80, anchor="center")
        tree.column("size", width=80, anchor="center")
        tree.column("location", width=250, anchor="w")
        
        # Add scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")
        hsb.grid(column=0, row=1, sticky="ew")
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        
        # Populate with data
        for entry in self.download_history:
            tree.insert("", "end", values=(
                entry.get("date", ""),
                entry.get("title", ""),
                entry.get("quality", ""),
                entry.get("size_mb", ""),
                entry.get("filename", "")
            ))
        
        # Add actions button frame
        btn_frame = ttk.Frame(history_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Button to open file location
        def open_selected_file_location():
            selected = tree.selection()
            if selected:
                item = tree.item(selected[0])
                file_path = item['values'][4]  # index 4 is the location
                if os.path.exists(os.path.dirname(file_path)):
                    if os.name == 'nt':  # Windows
                        os.startfile(os.path.dirname(file_path))
                    else:
                        try:
                            if os.uname().sysname == 'Linux':
                                subprocess.call(['xdg-open', os.path.dirname(file_path)])
                            else:
                                subprocess.call(['open', os.path.dirname(file_path)])
                        except:
                            pass
                else:
                    messagebox.showerror("Error", "Directory no longer exists")
        
        # Button to clear history
        def clear_history():
            if messagebox.askyesno("Clear History", "Are you sure you want to clear download history?"):
                self.download_history = []
                self.save_download_history()
                history_window.destroy()
        
        # Add buttons
        open_btn = ttk.Button(btn_frame, text="Open File Location", command=open_selected_file_location)
        open_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="Clear History", command=clear_history)
        clear_btn.pack(side=tk.RIGHT, padx=5)
        
    def browse_directory(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dir_var.set(folder)
            
    def open_download_folder(self):
        folder = self.dir_var.get()
        if os.path.exists(folder):
            try:
                # Open file explorer to the folder
                if os.name == 'nt':  # Windows
                    os.startfile(folder)
                elif os.name == 'posix':  # macOS, Linux
                    subprocess.call(('xdg-open', folder) if os.uname().sysname == 'Linux' else ('open', folder))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {str(e)}")
        else:
            messagebox.showerror("Error", "The specified folder does not exist")
    
    def update_progress(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%')
            p = p.replace('%', '')
            try:
                self.progress_var.set(float(p))
            except:
                pass
            self.status_var.set(f"{d.get('_percent_str', '0%')} complete - {d.get('_speed_str', 'N/A')}")
            self.root.update_idletasks()
        elif d['status'] == 'finished':
            # Store the downloaded file path
            self.downloaded_file_path = d.get('filename')
    
    def download_video(self):
        url = self.url_var.get()
        save_path = self.dir_var.get()
        quality_name = self.quality_combobox.get()
        format_string = self.quality_map[quality_name]
        
        try:
            self.status_var.set("Fetching video info...")
            self.root.update_idletasks()
            
            ydl_opts = {
                'format': format_string,
                'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'progress_hooks': [self.update_progress],
            }
            
            # For audio-only, convert to MP3
            if quality_name == "Audio Only (MP3)":
                ydl_opts.update({
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            
            # Check if user selected 4K or 1080p but FFmpeg is not installed
            high_quality = quality_name in ["4K", "1080p"]
            if high_quality and not self.ffmpeg_installed:
                self.status_var.set("Warning: FFmpeg not installed. Quality may be limited.")
                self.root.update_idletasks()
            
            # First get metadata
            with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as meta_ydl:
                info = meta_ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown Title')
                
            # Then download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            self.status_var.set("Download completed successfully!")
            
            # Add to history
            if self.downloaded_file_path:
                file_size_mb = round(os.path.getsize(self.downloaded_file_path) / (1024 * 1024), 2)
                self.add_to_history(
                    url=url,
                    title=title,
                    filename=self.downloaded_file_path,
                    quality=quality_name,
                    size_mb=file_size_mb
                )
            
            # Show success message with option to open folder
            result = messagebox.askquestion("Success", 
                                           "Video downloaded successfully!\nWould you like to open the download location?",
                                           icon='info')
            if result == 'yes':
                self.open_download_folder()
                
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        self.download_btn["state"] = "normal"
    
    def start_download(self):
        if not self.url_var.get():
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
            
        if not self.dir_var.get():
            messagebox.showerror("Error", "Please select a save location")
            return
            
        # Ensure the directory exists
        save_dir = self.dir_var.get()
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create directory: {str(e)}")
                return
                
        self.download_btn["state"] = "disabled"
        self.progress_var.set(0)
        self.status_var.set("Starting download...")
        
        # Run download in a separate thread
        thread = threading.Thread(target=self.download_video)
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = YoutubeDownloader(root)
    root.mainloop()
