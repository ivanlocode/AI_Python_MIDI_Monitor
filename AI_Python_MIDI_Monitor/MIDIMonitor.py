import tkinter as tk
from tkinter import ttk, scrolledtext
import pygame
import pygame.midi
import threading
import time
from datetime import datetime


class MIDIMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDI Input Monitor")
        self.root.geometry("800x600")

        # Initialize MIDI
        pygame.midi.init()
        self.input_device = None
        self.is_monitoring = False

        # Create GUI
        self.create_widgets()

        # Start MIDI monitoring thread
        self.monitor_thread = None

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="MIDI Input Monitor", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        # Device selection
        device_frame = ttk.Frame(main_frame)
        device_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(device_frame, text="MIDI Input Device:").pack(side=tk.LEFT)

        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(device_frame, textvariable=self.device_var, width=30)
        self.device_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_selected)

        # Refresh button
        refresh_btn = ttk.Button(device_frame, text="Refresh Devices", command=self.refresh_devices)
        refresh_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10))

        self.start_btn = ttk.Button(control_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_btn = ttk.Button(control_frame, text="Stop Monitoring", command=self.stop_monitoring,
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Status label
        self.status_var = tk.StringVar(value="Status: Not monitoring")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=3, column=0, columnspan=3, pady=(0, 10))

        # Log display
        log_frame = ttk.LabelFrame(main_frame, text="MIDI Events", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Configure grid weights for log frame
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=80, wrap=tk.NONE)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Clear button
        clear_btn = ttk.Button(main_frame, text="Clear Log", command=self.clear_log)
        clear_btn.grid(row=5, column=0, columnspan=3, pady=(0, 10))

        # Initialize device list
        self.refresh_devices()

    def refresh_devices(self):
        """Refresh the list of available MIDI input devices"""
        self.device_combo['values'] = []
        self.device_var.set("")

        device_count = pygame.midi.get_count()
        devices = []

        for i in range(device_count):
            info = pygame.midi.get_device_info(i)
            if info[2] == 1:  # Input device
                name = info[1].decode('utf-8') if isinstance(info[1], bytes) else info[1]
                devices.append(f"{i}: {name}")

        self.device_combo['values'] = devices

        if devices:
            self.device_combo.current(0)
            self.status_var.set("Status: Ready - Select device")
        else:
            self.status_var.set("Status: No MIDI input devices found")

    def on_device_selected(self, event):
        """Handle device selection"""
        selected = self.device_var.get()
        if selected:
            self.status_var.set(f"Status: Device selected - {selected}")

    def start_monitoring(self):
        """Start monitoring MIDI input"""
        if not self.is_monitoring:
            selected = self.device_var.get()
            if not selected:
                self.log_message("Error: Please select a device first")
                return

            try:
                # Get device ID from selection
                device_id = int(selected.split(':')[0])

                # Open device
                self.input_device = pygame.midi.Input(device_id)
                self.is_monitoring = True

                # Update UI
                self.start_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)
                self.status_var.set(f"Status: Monitoring device {device_id}")

                # Start monitoring thread
                self.monitor_thread = threading.Thread(target=self.monitor_midi, daemon=True)
                self.monitor_thread.start()

            except Exception as e:
                self.log_message(f"Error starting monitoring: {str(e)}")

    def stop_monitoring(self):
        """Stop monitoring MIDI input"""
        if self.is_monitoring:
            self.is_monitoring = False

            # Close device
            if self.input_device:
                self.input_device.close()
                self.input_device = None

            # Update UI
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_var.set("Status: Monitoring stopped")

    def monitor_midi(self):
        """Monitor MIDI input in a separate thread"""
        while self.is_monitoring:
            try:
                if self.input_device and self.input_device.poll():
                    midi_events = self.input_device.read(10)
                    for event in midi_events:
                        data = event[0]
                        timestamp = event[1]

                        # Parse MIDI message
                        msg_type = data[0] & 0xF0
                        channel = data[0] & 0x0F

                        message = ""
                        if msg_type == 0x80:  # Note Off
                            message = f"Note Off - Channel {channel + 1}, Note {data[1]}, Velocity {data[2]}"
                        elif msg_type == 0x90:  # Note On
                            message = f"Note On - Channel {channel + 1}, Note {data[1]}, Velocity {data[2]}"
                        elif msg_type == 0xB0:  # Control Change
                            message = f"Control Change - Channel {channel + 1}, Controller {data[1]}, Value {data[2]}"
                        elif msg_type == 0xC0:  # Program Change
                            message = f"Program Change - Channel {channel + 1}, Program {data[1]}"
                        elif msg_type == 0xD0:  # Aftertouch
                            message = f"Aftertouch - Channel {channel + 1}, Value {data[1]}"
                        elif msg_type == 0xE0:  # Pitch Bend
                            message = f"Pitch Bend - Channel {channel + 1}, Value {data[1] + (data[2] << 7)}"
                        else:
                            message = f"MIDI Message - Type {hex(msg_type)}, Channel {channel + 1}"

                        # Log the message
                        self.log_message(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

                time.sleep(0.01)  # Small delay to prevent high CPU usage

            except Exception as e:
                if self.is_monitoring:  # Only log if we're still monitoring
                    self.log_message(f"Error processing MIDI event: {str(e)}")

    def log_message(self, message):
        """Add a message to the log display"""
        self.root.after(0, lambda: self.log_text.insert(tk.END, f"{message}\n"))
        self.root.after(0, lambda: self.log_text.see(tk.END))

    def clear_log(self):
        """Clear the log display"""
        self.log_text.delete(1.0, tk.END)

    def on_closing(self):
        """Handle window closing"""
        self.stop_monitoring()
        pygame.midi.quit()
        self.root.destroy()


def main():
    # Initialize pygame MIDI
    try:
        pygame.midi.init()
    except Exception as e:
        print(f"Failed to initialize pygame MIDI: {e}")
        return

    # Create GUI
    root = tk.Tk()
    app = MIDIMonitor(root)

    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        app.on_closing()


if __name__ == "__main__":
    main()
