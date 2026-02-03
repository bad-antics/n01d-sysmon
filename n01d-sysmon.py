#!/usr/bin/env python3
"""
███╗   ██╗ ██████╗  ██╗██████╗       ███████╗██╗   ██╗███████╗███╗   ███╗ ██████╗ ███╗   ██╗
████╗  ██║██╔═████╗███║██╔══██╗      ██╔════╝╚██╗ ██╔╝██╔════╝████╗ ████║██╔═══██╗████╗  ██║
██╔██╗ ██║██║██╔██║╚██║██║  ██║█████╗███████╗ ╚████╔╝ ███████╗██╔████╔██║██║   ██║██╔██╗ ██║
██║╚██╗██║████╔╝██║ ██║██║  ██║╚════╝╚════██║  ╚██╔╝  ╚════██║██║╚██╔╝██║██║   ██║██║╚██╗██║
██║ ╚████║╚██████╔╝ ██║██████╔╝      ███████║   ██║   ███████║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║
╚═╝  ╚═══╝ ╚═════╝  ╚═╝╚═════╝       ╚══════╝   ╚═╝   ╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝

N01D System Monitor - Real-time system monitoring with hacker aesthetics
Part of the NullSec Toolkit
"""

import customtkinter as ctk
import psutil
import platform
import subprocess
import threading
import time
from datetime import datetime, timedelta
from collections import deque
from typing import Optional, Dict, List, Callable
import socket
import os


VERSION = "1.0.0"
APP_NAME = "N01D SysMon"


class N01DTheme:
    """N01D hacker theme"""
    
    def __init__(self):
        self.colors = {
            'bg_dark': '#0a0a0f',
            'bg': '#12121a',
            'bg_light': '#1a1a2e',
            'bg_lighter': '#252538',
            'accent': '#00ff88',
            'accent_dim': '#00cc66',
            'accent_hover': '#00dd77',
            'warning': '#ffaa00',
            'danger': '#ff3366',
            'info': '#00aaff',
            'text': '#e0e0e0',
            'text_dim': '#888888',
            'border': '#333344',
            'graph_cpu': '#00ff88',
            'graph_mem': '#ff6b9d',
            'graph_net_up': '#00aaff',
            'graph_net_down': '#ffaa00',
            'graph_disk': '#aa88ff',
        }
        
    def apply(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")


class GraphWidget(ctk.CTkFrame):
    """Real-time graph widget using canvas"""
    
    def __init__(self, master, title: str, color: str, max_value: float = 100.0, 
                 unit: str = "%", history_size: int = 60, **kwargs):
        super().__init__(master, **kwargs)
        
        self.title = title
        self.color = color
        self.max_value = max_value
        self.unit = unit
        self.history = deque([0.0] * history_size, maxlen=history_size)
        
        self.configure(fg_color="#1a1a2e", corner_radius=10)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        self.title_label = ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family="JetBrains Mono", size=12, weight="bold"),
            text_color="#888"
        )
        self.title_label.pack(side="left")
        
        self.value_label = ctk.CTkLabel(
            header,
            text="0.0%",
            font=ctk.CTkFont(family="JetBrains Mono", size=14, weight="bold"),
            text_color=color
        )
        self.value_label.pack(side="right")
        
        # Canvas for graph
        self.canvas = ctk.CTkCanvas(
            self,
            bg="#12121a",
            highlightthickness=0,
            height=80
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.canvas.bind("<Configure>", self._on_resize)
        
    def _on_resize(self, event):
        self._draw_graph()
        
    def update_value(self, value: float):
        """Update with new value and redraw"""
        self.history.append(min(value, self.max_value))
        
        if self.unit == "%":
            display = f"{value:.1f}%"
        elif self.unit == "MB/s":
            display = f"{value:.1f} MB/s"
        elif self.unit == "GB":
            display = f"{value:.1f} GB"
        else:
            display = f"{value:.1f} {self.unit}"
            
        self.value_label.configure(text=display)
        self._draw_graph()
        
    def _draw_graph(self):
        """Draw the graph on canvas"""
        self.canvas.delete("all")
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 10 or height < 10:
            return
            
        # Draw grid lines
        for i in range(1, 4):
            y = height * i / 4
            self.canvas.create_line(0, y, width, y, fill="#252538", dash=(2, 4))
            
        # Draw data
        if not self.history:
            return
            
        points = []
        data_len = len(self.history)
        
        for i, val in enumerate(self.history):
            x = (i / (data_len - 1)) * width if data_len > 1 else width / 2
            y = height - (val / self.max_value) * height
            points.extend([x, y])
            
        if len(points) >= 4:
            # Fill area
            fill_points = [0, height] + points + [width, height]
            self.canvas.create_polygon(fill_points, fill=self.color + "20", outline="")
            
            # Draw line
            self.canvas.create_line(points, fill=self.color, width=2, smooth=True)


class ProcessList(ctk.CTkFrame):
    """Process list with sorting and filtering"""
    
    def __init__(self, master, theme: N01DTheme, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = theme
        
        self.configure(fg_color="#1a1a2e", corner_radius=10)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            header,
            text="🔄 Processes",
            font=ctk.CTkFont(family="JetBrains Mono", size=14, weight="bold")
        ).pack(side="left")
        
        # Sort options
        self.sort_var = ctk.StringVar(value="cpu")
        sort_menu = ctk.CTkOptionMenu(
            header,
            values=["cpu", "memory", "pid", "name"],
            variable=self.sort_var,
            font=ctk.CTkFont(family="JetBrains Mono", size=10),
            width=80,
            height=25,
            command=self._refresh
        )
        sort_menu.pack(side="right")
        
        ctk.CTkLabel(
            header,
            text="Sort by:",
            font=ctk.CTkFont(family="JetBrains Mono", size=10),
            text_color="#888"
        ).pack(side="right", padx=(0, 5))
        
        # Search
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh())
        
        search = ctk.CTkEntry(
            self,
            placeholder_text="🔍 Filter processes...",
            textvariable=self.search_var,
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            height=30
        )
        search.pack(fill="x", padx=10, pady=(0, 10))
        
        # Column headers
        headers = ctk.CTkFrame(self, fg_color="#252538")
        headers.pack(fill="x", padx=10)
        
        cols = [("PID", 70), ("Name", 200), ("CPU %", 70), ("Mem %", 70), ("Status", 80)]
        for text, width in cols:
            ctk.CTkLabel(
                headers,
                text=text,
                font=ctk.CTkFont(family="JetBrains Mono", size=10, weight="bold"),
                width=width,
                anchor="w"
            ).pack(side="left", padx=5, pady=5)
            
        # Scrollable process list
        self.process_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.process_scroll.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        self._refresh()
        
    def _refresh(self, *args):
        """Refresh process list"""
        # Clear current
        for widget in self.process_scroll.winfo_children():
            widget.destroy()
            
        # Get processes
        processes = []
        search = self.search_var.get().lower()
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = proc.info
                if search and search not in info['name'].lower():
                    continue
                processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # Sort
        sort_key = self.sort_var.get()
        if sort_key == "cpu":
            processes.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
        elif sort_key == "memory":
            processes.sort(key=lambda x: x.get('memory_percent', 0) or 0, reverse=True)
        elif sort_key == "pid":
            processes.sort(key=lambda x: x.get('pid', 0))
        else:
            processes.sort(key=lambda x: x.get('name', '').lower())
            
        # Display top 50
        for proc in processes[:50]:
            row = ctk.CTkFrame(self.process_scroll, fg_color="transparent", height=25)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            
            # PID
            ctk.CTkLabel(
                row,
                text=str(proc.get('pid', '')),
                font=ctk.CTkFont(family="JetBrains Mono", size=10),
                width=70,
                anchor="w",
                text_color="#888"
            ).pack(side="left", padx=5)
            
            # Name
            name = proc.get('name', '')[:25]
            ctk.CTkLabel(
                row,
                text=name,
                font=ctk.CTkFont(family="JetBrains Mono", size=10),
                width=200,
                anchor="w"
            ).pack(side="left", padx=5)
            
            # CPU
            cpu = proc.get('cpu_percent', 0) or 0
            cpu_color = "#00ff88" if cpu < 20 else "#ffaa00" if cpu < 50 else "#ff3366"
            ctk.CTkLabel(
                row,
                text=f"{cpu:.1f}%",
                font=ctk.CTkFont(family="JetBrains Mono", size=10),
                width=70,
                anchor="w",
                text_color=cpu_color
            ).pack(side="left", padx=5)
            
            # Memory
            mem = proc.get('memory_percent', 0) or 0
            mem_color = "#00ff88" if mem < 10 else "#ffaa00" if mem < 30 else "#ff3366"
            ctk.CTkLabel(
                row,
                text=f"{mem:.1f}%",
                font=ctk.CTkFont(family="JetBrains Mono", size=10),
                width=70,
                anchor="w",
                text_color=mem_color
            ).pack(side="left", padx=5)
            
            # Status
            status = proc.get('status', 'unknown')
            status_color = "#00ff88" if status == 'running' else "#888"
            ctk.CTkLabel(
                row,
                text=status[:8],
                font=ctk.CTkFont(family="JetBrains Mono", size=10),
                width=80,
                anchor="w",
                text_color=status_color
            ).pack(side="left", padx=5)


class NetworkMonitor(ctk.CTkFrame):
    """Network interface monitor"""
    
    def __init__(self, master, theme: N01DTheme, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = theme
        self.last_bytes = {}
        
        self.configure(fg_color="#1a1a2e", corner_radius=10)
        
        # Header
        ctk.CTkLabel(
            self,
            text="🌐 Network Interfaces",
            font=ctk.CTkFont(family="JetBrains Mono", size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        self.interfaces_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.interfaces_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self._refresh()
        
    def _refresh(self):
        """Refresh network stats"""
        for widget in self.interfaces_frame.winfo_children():
            widget.destroy()
            
        try:
            net_io = psutil.net_io_counters(pernic=True)
            addrs = psutil.net_if_addrs()
            
            for iface, stats in net_io.items():
                if iface == 'lo':
                    continue
                    
                frame = ctk.CTkFrame(self.interfaces_frame, fg_color="#252538", corner_radius=8)
                frame.pack(fill="x", pady=3)
                
                # Interface name and IP
                info_frame = ctk.CTkFrame(frame, fg_color="transparent")
                info_frame.pack(fill="x", padx=10, pady=8)
                
                ctk.CTkLabel(
                    info_frame,
                    text=f"📡 {iface}",
                    font=ctk.CTkFont(family="JetBrains Mono", size=12, weight="bold")
                ).pack(side="left")
                
                # Get IP
                ip = "No IP"
                if iface in addrs:
                    for addr in addrs[iface]:
                        if addr.family == socket.AF_INET:
                            ip = addr.address
                            break
                            
                ctk.CTkLabel(
                    info_frame,
                    text=ip,
                    font=ctk.CTkFont(family="JetBrains Mono", size=10),
                    text_color="#888"
                ).pack(side="right")
                
                # Stats
                stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
                stats_frame.pack(fill="x", padx=10, pady=(0, 8))
                
                # Calculate speed
                prev = self.last_bytes.get(iface, (0, 0))
                down_speed = (stats.bytes_recv - prev[0]) / 1024 / 1024  # MB/s
                up_speed = (stats.bytes_sent - prev[1]) / 1024 / 1024
                self.last_bytes[iface] = (stats.bytes_recv, stats.bytes_sent)
                
                ctk.CTkLabel(
                    stats_frame,
                    text=f"↓ {down_speed:.2f} MB/s",
                    font=ctk.CTkFont(family="JetBrains Mono", size=10),
                    text_color="#00aaff"
                ).pack(side="left")
                
                ctk.CTkLabel(
                    stats_frame,
                    text=f"↑ {up_speed:.2f} MB/s",
                    font=ctk.CTkFont(family="JetBrains Mono", size=10),
                    text_color="#ffaa00"
                ).pack(side="left", padx=20)
                
                # Total
                total_down = stats.bytes_recv / 1024 / 1024 / 1024
                total_up = stats.bytes_sent / 1024 / 1024 / 1024
                ctk.CTkLabel(
                    stats_frame,
                    text=f"Total: ↓{total_down:.1f}GB ↑{total_up:.1f}GB",
                    font=ctk.CTkFont(family="JetBrains Mono", size=9),
                    text_color="#666"
                ).pack(side="right")
                
        except Exception as e:
            ctk.CTkLabel(
                self.interfaces_frame,
                text=f"Error: {str(e)}",
                text_color="#ff3366"
            ).pack()


class DiskMonitor(ctk.CTkFrame):
    """Disk usage monitor"""
    
    def __init__(self, master, theme: N01DTheme, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = theme
        
        self.configure(fg_color="#1a1a2e", corner_radius=10)
        
        ctk.CTkLabel(
            self,
            text="💾 Disk Usage",
            font=ctk.CTkFont(family="JetBrains Mono", size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        self.disks_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.disks_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self._refresh()
        
    def _refresh(self):
        """Refresh disk stats"""
        for widget in self.disks_frame.winfo_children():
            widget.destroy()
            
        try:
            partitions = psutil.disk_partitions()
            
            for part in partitions:
                if 'loop' in part.device:
                    continue
                    
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except:
                    continue
                    
                frame = ctk.CTkFrame(self.disks_frame, fg_color="#252538", corner_radius=8)
                frame.pack(fill="x", pady=3)
                
                # Header
                header = ctk.CTkFrame(frame, fg_color="transparent")
                header.pack(fill="x", padx=10, pady=(8, 5))
                
                ctk.CTkLabel(
                    header,
                    text=f"📁 {part.mountpoint}",
                    font=ctk.CTkFont(family="JetBrains Mono", size=11, weight="bold")
                ).pack(side="left")
                
                percent = usage.percent
                color = "#00ff88" if percent < 70 else "#ffaa00" if percent < 90 else "#ff3366"
                ctk.CTkLabel(
                    header,
                    text=f"{percent:.1f}%",
                    font=ctk.CTkFont(family="JetBrains Mono", size=11, weight="bold"),
                    text_color=color
                ).pack(side="right")
                
                # Progress bar
                bar_frame = ctk.CTkFrame(frame, fg_color="#12121a", height=8, corner_radius=4)
                bar_frame.pack(fill="x", padx=10, pady=(0, 5))
                bar_frame.pack_propagate(False)
                
                fill = ctk.CTkFrame(bar_frame, fg_color=color, corner_radius=4)
                fill.place(relwidth=percent/100, relheight=1)
                
                # Details
                used_gb = usage.used / (1024**3)
                total_gb = usage.total / (1024**3)
                free_gb = usage.free / (1024**3)
                
                ctk.CTkLabel(
                    frame,
                    text=f"Used: {used_gb:.1f}GB / {total_gb:.1f}GB • Free: {free_gb:.1f}GB",
                    font=ctk.CTkFont(family="JetBrains Mono", size=9),
                    text_color="#666"
                ).pack(anchor="w", padx=10, pady=(0, 8))
                
        except Exception as e:
            ctk.CTkLabel(
                self.disks_frame,
                text=f"Error: {str(e)}",
                text_color="#ff3366"
            ).pack()


class SystemInfo(ctk.CTkFrame):
    """System information panel"""
    
    def __init__(self, master, theme: N01DTheme, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = theme
        
        self.configure(fg_color="#1a1a2e", corner_radius=10)
        
        ctk.CTkLabel(
            self,
            text="🖥️ System Info",
            font=ctk.CTkFont(family="JetBrains Mono", size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # Gather info
        info = [
            ("OS", f"{platform.system()} {platform.release()}"),
            ("Hostname", socket.gethostname()),
            ("Kernel", platform.version()[:40]),
            ("CPU", platform.processor()[:35] or "Unknown"),
            ("Cores", f"{psutil.cpu_count(logical=False)} physical / {psutil.cpu_count()} logical"),
            ("RAM", f"{psutil.virtual_memory().total / (1024**3):.1f} GB"),
            ("Uptime", self._get_uptime()),
        ]
        
        for label, value in info:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(
                row,
                text=f"{label}:",
                font=ctk.CTkFont(family="JetBrains Mono", size=10),
                text_color="#888",
                width=80,
                anchor="w"
            ).pack(side="left")
            
            ctk.CTkLabel(
                row,
                text=value,
                font=ctk.CTkFont(family="JetBrains Mono", size=10),
                anchor="w"
            ).pack(side="left")
            
    def _get_uptime(self) -> str:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes = remainder // 60
        return f"{days}d {hours}h {minutes}m"


class N01DSysMon(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.theme = N01DTheme()
        self.theme.apply()
        
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        self.configure(fg_color=self.theme.colors['bg_dark'])
        
        # Grid config
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_header()
        self._create_left_panel()
        self._create_right_panel()
        
        # Start monitoring
        self._start_monitoring()
        
        # Cleanup on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _create_header(self):
        """Create header with title"""
        header = ctk.CTkFrame(self, fg_color=self.theme.colors['bg'], corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        title = ctk.CTkLabel(
            header,
            text="N01D",
            font=ctk.CTkFont(family="JetBrains Mono", size=28, weight="bold"),
            text_color=self.theme.colors['accent']
        )
        title.pack(side="left", padx=20, pady=15)
        
        subtitle = ctk.CTkLabel(
            header,
            text="SYSTEM MONITOR",
            font=ctk.CTkFont(family="JetBrains Mono", size=12),
            text_color=self.theme.colors['text_dim']
        )
        subtitle.pack(side="left", pady=15)
        
        # Time display
        self.time_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(family="JetBrains Mono", size=14),
            text_color=self.theme.colors['accent']
        )
        self.time_label.pack(side="right", padx=20, pady=15)
        
    def _create_left_panel(self):
        """Create left panel with graphs"""
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.grid_rowconfigure((0, 1, 2, 3), weight=1)
        left.grid_columnconfigure(0, weight=1)
        
        # CPU Graph
        self.cpu_graph = GraphWidget(
            left, "CPU Usage", self.theme.colors['graph_cpu'],
            max_value=100, unit="%"
        )
        self.cpu_graph.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        
        # Memory Graph
        self.mem_graph = GraphWidget(
            left, "Memory Usage", self.theme.colors['graph_mem'],
            max_value=100, unit="%"
        )
        self.mem_graph.grid(row=1, column=0, sticky="nsew", pady=5)
        
        # Network Down Graph
        self.net_down_graph = GraphWidget(
            left, "Network ↓", self.theme.colors['graph_net_down'],
            max_value=10, unit="MB/s"
        )
        self.net_down_graph.grid(row=2, column=0, sticky="nsew", pady=5)
        
        # Network Up Graph  
        self.net_up_graph = GraphWidget(
            left, "Network ↑", self.theme.colors['graph_net_up'],
            max_value=10, unit="MB/s"
        )
        self.net_up_graph.grid(row=3, column=0, sticky="nsew", pady=(5, 0))
        
    def _create_right_panel(self):
        """Create right panel with details"""
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        
        # Top row - System Info, Disks, Network
        top = ctk.CTkFrame(right, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        top.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.sys_info = SystemInfo(top, self.theme)
        self.sys_info.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        self.disk_mon = DiskMonitor(top, self.theme)
        self.disk_mon.grid(row=0, column=1, sticky="nsew", padx=5)
        
        self.net_mon = NetworkMonitor(top, self.theme)
        self.net_mon.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        # Process list
        self.proc_list = ProcessList(right, self.theme)
        self.proc_list.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        
    def _start_monitoring(self):
        """Start background monitoring thread"""
        self.running = True
        self.last_net = psutil.net_io_counters()
        
        def monitor():
            while self.running:
                try:
                    # CPU
                    cpu = psutil.cpu_percent(interval=0.5)
                    self.cpu_graph.update_value(cpu)
                    
                    # Memory
                    mem = psutil.virtual_memory().percent
                    self.mem_graph.update_value(mem)
                    
                    # Network
                    net = psutil.net_io_counters()
                    down_speed = (net.bytes_recv - self.last_net.bytes_recv) / 1024 / 1024
                    up_speed = (net.bytes_sent - self.last_net.bytes_sent) / 1024 / 1024
                    self.last_net = net
                    
                    self.net_down_graph.update_value(down_speed)
                    self.net_up_graph.update_value(up_speed)
                    
                    # Update time
                    self.time_label.configure(
                        text=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    
                except Exception as e:
                    pass
                    
                time.sleep(1)
                
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        
        # Periodic refresh of other panels
        def refresh_panels():
            if self.running:
                try:
                    self.proc_list._refresh()
                    self.disk_mon._refresh()
                    self.net_mon._refresh()
                except:
                    pass
                self.after(5000, refresh_panels)
                
        self.after(5000, refresh_panels)
        
    def _on_close(self):
        """Clean up on close"""
        self.running = False
        self.destroy()


def main():
    app = N01DSysMon()
    app.mainloop()
    

if __name__ == "__main__":
    main()
