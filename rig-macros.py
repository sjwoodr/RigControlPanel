#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N9OH Rig Control Panel - IC-7300 Radio Control Application

A comprehensive GUI application for controlling an Icom IC-7300 radio with
advanced features including voice keying, QSO recording, and text-to-speech
transmission via PulseAudio.

Author: Steve Woodruff, N9OH
License: MIT

Copyright (c) 2026 Steve Woodruff, N9OH

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import xmlrpc.client
import sys
from functools import partial
from datetime import datetime
import subprocess
import threading
import queue
import serial
import time
import configparser

import os

VERSION = "1.0.0"

log_path = r"/tmp/rig-macros-error.log"

class Logger:
    def __init__(self, filename):
        self.log = open(filename, "w", buffering=1)  # write (truncate) mode, line-buffered

    def write(self, message):
        if message.strip():
            if not message.endswith("\n"):
                message += "\n"
            self.log.write(message)
            self.log.flush()

    def flush(self):
        self.log.flush()

sys.stderr = Logger(log_path)
sys.stdout = Logger(log_path)
print("=== Rig Macros Script Started ===", file=sys.stderr)

# Load configuration file
config = configparser.ConfigParser()
config_file = os.path.join(os.path.dirname(__file__), 'rig-macros.conf')
if os.path.exists(config_file):
    config.read(config_file)
    print(f"Loaded configuration from: {config_file}", file=sys.stderr)
else:
    print(f"Warning: Configuration file not found at {config_file}", file=sys.stderr)
    print("Using default values", file=sys.stderr)

# Ensure Piper voice model is downloaded at startup
def ensure_piper_model(debug_queue=None):
    voice_model = "en_US-hfc_male-medium"
    msg = f"Checking for Piper voice model: {voice_model}"
    print(msg, file=sys.stderr)
    if debug_queue:
        timestamp = datetime.now().strftime("%H:%M:%S")
        debug_queue.put(f"[{timestamp}] {msg}")
    
    try:
        result = subprocess.run(
            ["python3", "-m", "piper.download_voices", voice_model],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            msg = f"Piper voice model '{voice_model}' downloaded and ready"
            print(msg, file=sys.stderr)
            if debug_queue:
                timestamp = datetime.now().strftime("%H:%M:%S")
                debug_queue.put(f"[{timestamp}] {msg}")
            return True
        else:
            msg = f"Failed to download Piper voice model: {result.stderr}"
            print(msg, file=sys.stderr)
            if debug_queue:
                timestamp = datetime.now().strftime("%H:%M:%S")
                debug_queue.put(f"[{timestamp}] {msg}")
            return False
    except subprocess.TimeoutExpired:
        msg = f"Piper model download timed out (5 min timeout exceeded)"
        print(msg, file=sys.stderr)
        if debug_queue:
            timestamp = datetime.now().strftime("%H:%M:%S")
            debug_queue.put(f"[{timestamp}] {msg}")
        return False
    except Exception as e:
        msg = f"Error checking Piper voice model: {e}"
        print(msg, file=sys.stderr)
        if debug_queue:
            timestamp = datetime.now().strftime("%H:%M:%S")
            debug_queue.put(f"[{timestamp}] {msg}")
        return False

# Open serial port once at startup and keep it open with both RTS and DTR LOW
serial_port = None
try:
    serial_port = serial.Serial('/dev/ttyUSB0', 19200, timeout=0.1)
    serial_port.rts = False  # Keep RTS LOW (no PTT)
    serial_port.dtr = False  # Keep DTR LOW (no CW keying)
    print(f"Serial port opened with RTS=LOW, DTR=LOW", file=sys.stderr)
except Exception as e:
    print(f"Warning: Could not open serial port: {e}", file=sys.stderr)

try:
    # Connect to FLRig
    flrig = xmlrpc.client.ServerProxy("http://localhost:12345")

    # Pre-generate TTS audio files at startup (will use debug_queue once GUI is ready)
    def generate_tts_file(text, filename, debug_queue=None, length_scale="0.72"):
        try:
            piper_cmd = [
                "piper",
                "--model", "en_US-hfc_male-medium",
                "--output_file", filename,
                "--length-scale", length_scale
            ]
            piper_process = subprocess.Popen(
                piper_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            piper_output, piper_error = piper_process.communicate(input=text.encode() + b"\n")
            if piper_process.returncode == 0 and os.path.exists(filename):
                file_size = os.path.getsize(filename)
                msg = f"Pre-generated TTS: {filename} ({file_size} bytes)"
                print(msg, file=sys.stderr)
                if debug_queue:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    debug_queue.put(f"[{timestamp}] {msg}")
                return True
            else:
                msg = f"TTS generation failed for {filename}: {piper_error.decode()}"
                print(msg, file=sys.stderr)
                if debug_queue:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    debug_queue.put(f"[{timestamp}] {msg}")
                return False
        except Exception as e:
            msg = f"TTS generation error: {e}"
            print(msg, file=sys.stderr)
            if debug_queue:
                timestamp = datetime.now().strftime("%H:%M:%S")
                debug_queue.put(f"[{timestamp}] {msg}")
            return False

    # Pre-generate TTS files in background (will be called later with debug_queue)
    def pre_generate_tts(debug_queue=None):
        msg = "Pre-generating TTS audio files..."
        print(msg, file=sys.stderr)
        if debug_queue:
            timestamp = datetime.now().strftime("%H:%M:%S")
            debug_queue.put(f"[{timestamp}] {msg}")
        
        button1_text = config.get('Piper TTS', 'button1_text', fallback=",, November Nine Oscar HOTEL")
        button1_scale = config.get('Piper TTS', 'button1_length_scale', fallback="0.72")
        button2_text = config.get('Piper TTS', 'button2_text', fallback="Thanks, also FIVE NINE")
        button2_scale = config.get('Piper TTS', 'button2_length_scale', fallback="0.72")
        button3_text = config.get('Piper TTS', 'button3_text', fallback="Seventy-Three")
        button3_scale = config.get('Piper TTS', 'button3_length_scale', fallback="0.55")
        
        generate_tts_file(button1_text, "/tmp/tts_n9oh.wav", debug_queue, button1_scale)
        generate_tts_file(button2_text, "/tmp/tts_tu59.wav", debug_queue, button2_scale)
        generate_tts_file(button3_text, "/tmp/tts_73.wav", debug_queue, button3_scale)
        msg = "TTS pre-generation complete"
        print(msg, file=sys.stderr)
        if debug_queue:
            timestamp = datetime.now().strftime("%H:%M:%S")
            debug_queue.put(f"[{timestamp}] {msg}")

    # GUI setup
    root = tk.Tk()
    root.title(f"N9OH Rig Control Panel v{VERSION}")

    # Status labels
    status_var = tk.StringVar()
    status_label = tk.Label(root, textvariable=status_var, fg="blue", font=("TkDefaultFont", 14))
    status_label.pack(pady=5)
    
    # VFO B status label (shown when split is enabled)
    status_b_var = tk.StringVar()
    status_b_label = tk.Label(root, textvariable=status_b_var, fg="green", font=("TkDefaultFont", 12))
    # Initially not packed - will be shown when split is enabled

    def poll_rig_status():
        try:
            freq_hz = float(flrig.rig.get_vfoA())
            mode = flrig.rig.get_mode()
            vfo = flrig.rig.get_AB()
            split = flrig.rig.get_split()
            split_txt = "Split ON" if split == 1 else "Split OFF"
            status_var.set(f"{mode} @ {freq_hz / 1e6:.3f} MHz | VFO {vfo} | {split_txt}")
            split_indicator.config(bg="yellow" if split == 1 else "gray")
            
            # Show VFO B status when split is enabled
            if split == 1:
                freq_b_hz = float(flrig.rig.get_vfoB())
                mode_b = flrig.rig.get_modeB()
                status_b_var.set(f"{mode_b} @ {freq_b_hz / 1e6:.3f} MHz | VFO B")
                status_b_label.pack(pady=(0, 5), before=top_frame)
            else:
                status_b_label.pack_forget()
                
        except Exception as e:
            print(f"Rig status poll error: {e}\n", file=sys.stderr)
        finally:
            root.after(2000, poll_rig_status)

    def toggle_split():
        try:
            current_split = flrig.rig.get_split()
            new_split = 0 if current_split == 1 else 1
            flrig.rig.set_split(new_split)
            status_var.set(f"Split mode: {'ON' if new_split == 1 else 'OFF'}")
            split_indicator.config(bg="yellow" if new_split == 1 else "gray")
        except Exception as e:
            status_var.set(f"Error: {e}")
            print(f"Split toggle error: {e}", file=sys.stderr)


    def toggle_vfo():
        try:
            current_vfo = flrig.rig.get_AB()
            new_vfo = "B" if current_vfo == "A" else "A"
            flrig.rig.set_AB(new_vfo)
            status_var.set(f"Switched to VFO {new_vfo}")
        except Exception as e:
            status_var.set(f"Error: {e}")
            print(f"VFO toggle error: {e}", file=sys.stderr)


    # Function to copy VFO A to B
    def run_vfo_copy():
        try:
            flrig.rig.vfoA2B()
            status_var.set("VFO A → B copied")
        except Exception as e:
            status_var.set(f"Error: {e}")
            print(f"VFO copy error: {e}", file=sys.stderr)

    # Function to set frequency and mode
    def set_freq_and_mode(freq_hz, mode):
        try:
            flrig.main.set_frequency(freq_hz)
            flrig.rig.set_mode(mode)
            status_var.set(f"{mode} @ {freq_hz / 1e6:.3f} MHz")
        except Exception as e:
            status_var.set(f"Error: {e}")
            print(f"Freq/mode error ({freq_hz}, {mode}): {e}", file=sys.stderr)

    # Button frame for top row
    top_frame = tk.Frame(root)
    top_frame.pack(padx=10, pady=(0, 4))  # top=0px, bottom=4px

    btn_vfo = tk.Button(top_frame, text="Copy VFO A → B", command=run_vfo_copy)
    btn_vfo.pack(side=tk.LEFT, padx=5, pady=0)
    
    btn_toggle = tk.Button(top_frame, text="VFO A/B", command=toggle_vfo)
    btn_toggle.pack(side=tk.LEFT, padx=5, pady=0)

    btn_split = tk.Button(top_frame, text="Split", command=toggle_split)
    btn_split.pack(side=tk.LEFT, padx=5, pady=0)

    split_indicator = tk.Label(top_frame, width=2, height=1, bg="gray", relief=tk.SUNKEN, bd=1)
    split_indicator.pack(side=tk.LEFT, padx=(5, 0))


    # CW Band Frame
    cw_frame = tk.LabelFrame(root, text="CW", padx=10, pady=10, bd=2, relief=tk.GROOVE)
    cw_frame.pack(padx=10, pady=5)

    cw_bands = {
        "10m": 28000000.0,
        "12m": 24900000.0,
        "15m": 21000000.0,
        "20m": 14000000.0,
        "40m":  7000000.0
    }

    for label, freq in cw_bands.items():
        btn = tk.Button(cw_frame, text=label, width=6,
                        command=partial(set_freq_and_mode, freq, "CW"))
        btn.pack(side=tk.LEFT, padx=5)

    # SSB Band Frame
    ssb_frame = tk.LabelFrame(root, text="SSB", padx=10, pady=10, bd=2, relief=tk.GROOVE)
    ssb_frame.pack(padx=10, pady=5)

    ssb_bands = {
        "10m": (28300000.0, "USB"),
        "12m": (24952000.0, "USB"),
        "15m": (21200000.0, "USB"),
        "20m": (14150000.0, "USB"),
        "40m": (7125000.0, "LSB")
    }

    for label, (freq, mode) in ssb_bands.items():
        btn = tk.Button(ssb_frame, text=label, width=6,
                        command=partial(set_freq_and_mode, freq, mode))
        btn.pack(side=tk.LEFT, padx=5)

    # Recording state
    recording_process = None
    current_recording_file = None
    recording_was_saved = False  # Track if current recording has been saved
    debug_queue = queue.Queue()
    
    # Ensure Piper voice model is downloaded (with debug queue available now)
    ensure_piper_model(debug_queue)
    
    # Function to add debug output
    def add_debug(message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        debug_queue.put(f"[{timestamp}] {message}")
    
    # Function to process debug queue and update text widget
    def process_debug_queue():
        try:
            while True:
                message = debug_queue.get_nowait()
                debug_text.insert(tk.END, message + "\n")
                debug_text.see(tk.END)
        except queue.Empty:
            pass
        finally:
            root.after(100, process_debug_queue)
    
    # Start TTS pre-generation in background now that debug_queue is ready
    tts_gen_thread = threading.Thread(target=pre_generate_tts, args=(debug_queue,), daemon=True)
    tts_gen_thread.start()
    
    # Function to read subprocess output in a thread
    def read_subprocess_output(process, stream_name):
        try:
            for line in iter(process.stderr.readline, b''):
                if line:
                    add_debug(f"{stream_name}: {line.decode('utf-8', errors='replace').rstrip()}")
        except Exception as e:
            add_debug(f"Error reading {stream_name}: {e}")
    
    # Function to toggle recording
    def toggle_recording():
        global recording_process, current_recording_file, recording_was_saved
        try:
            if recording_process is None:
                # Start recording
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"/tmp/qso-{timestamp}.mp3"
                current_recording_file = output_file
                recording_was_saved = False  # Reset saved flag for new recording
                
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "pulse", "-i", "alsa_input.usb-Burr-Brown_from_TI_USB_Audio_CODEC-00.analog-stereo",
                    "-f", "pulse", "-i", "alsa_input.usb-SHENZHEN_Fullhan_HD_4MP_WEBCAM_20200506-02.mono-fallback",
                    "-filter_complex", "[0:a][1:a]amerge=inputs=2[aout]",
                    "-map", "[aout]", "-ac", "2", output_file
                ]
                
                recording_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
                add_debug(f"Recording started: {output_file}")
                add_debug(f"FFmpeg command: {' '.join(cmd)}")
                
                # Start thread to read ffmpeg output
                threading.Thread(target=read_subprocess_output, args=(recording_process, "ffmpeg"), daemon=True).start()
                
                status_var.set(f"Recording started: {output_file}")
                btn_rec.config(bg="red", fg="white")
            else:
                # Stop recording
                add_debug("Stopping recording...")
                recording_process.terminate()
                try:
                    recording_process.wait(timeout=2)
                    add_debug("Recording stopped successfully")
                except subprocess.TimeoutExpired:
                    recording_process.kill()
                    add_debug("Recording killed (timeout)")
                recording_process = None
                filename = os.path.basename(current_recording_file) if current_recording_file else "recording"
                status_var.set(f"Recording stopped: {filename}")
                btn_rec.config(bg=default_btn_bg, fg=default_btn_fg)
        except Exception as e:
            status_var.set(f"Error: {e}")
            print(f"Recording error: {e}", file=sys.stderr)
            recording_process = None
            btn_rec.config(bg=default_btn_bg, fg=default_btn_fg)
    
    # Function to delete the last recording
    def delete_recording():
        global recording_process, current_recording_file, recording_was_saved
        try:
            # Check if file exists
            if not current_recording_file or not os.path.exists(current_recording_file):
                status_var.set("No recording to delete")
                return
            
            # If recording was saved, ask for confirmation
            if recording_was_saved:
                filename = os.path.basename(current_recording_file)
                result = messagebox.askyesno(
                    "Confirm Delete",
                    f"This recording has been saved.\n\n{filename}\n\nAre you sure you want to delete it?",
                    icon='warning'
                )
                if not result:
                    status_var.set("Delete cancelled")
                    return
            
            # Stop recording if active
            if recording_process is not None:
                recording_process.terminate()
                try:
                    recording_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    recording_process.kill()
                recording_process = None
            
            # Delete the file
            os.remove(current_recording_file)
            add_debug(f"Deleted: {current_recording_file}")
            status_var.set(f"Deleted: {os.path.basename(current_recording_file)}")
            current_recording_file = None
            recording_was_saved = False
            
            # Always reset button when deleting
            btn_rec.config(bg=default_btn_bg, fg=default_btn_fg)
        except Exception as e:
            status_var.set(f"Delete error: {e}")
            print(f"Delete error: {e}", file=sys.stderr)
            # Reset button even on error
            btn_rec.config(bg=default_btn_bg, fg=default_btn_fg)
            recording_process = None
    
    # Function to play the last recording
    def play_recording():
        try:
            if current_recording_file and os.path.exists(current_recording_file):
                subprocess.Popen(["vlc", current_recording_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                add_debug(f"Playing: {current_recording_file}")
                status_var.set(f"Playing: {os.path.basename(current_recording_file)}")
            else:
                status_var.set("No recording to play")
        except Exception as e:
            status_var.set(f"Play error: {e}")
            print(f"Play error: {e}", file=sys.stderr)
    
    # Function to save the recording to a new location
    def save_recording():
        global current_recording_file, recording_was_saved
        try:
            if current_recording_file and os.path.exists(current_recording_file):
                # Get initial filename suggestion
                initial_filename = os.path.basename(current_recording_file)
                
                # Default save directory
                default_save_dir = os.path.expanduser("~/Documents/QSO Recordings")
                
                # Open file save dialog
                save_path = filedialog.asksaveasfilename(
                    initialdir=default_save_dir,
                    initialfile=initial_filename,
                    title="Save Recording As",
                    filetypes=[("MP3 files", "*.mp3"), ("All files", "*.*")],
                    defaultextension=".mp3"
                )
                
                if save_path:
                    # Create directory if it doesn't exist
                    save_dir = os.path.dirname(save_path)
                    if save_dir and not os.path.exists(save_dir):
                        os.makedirs(save_dir, exist_ok=True)
                    
                    # Use mv command to move the file
                    result = subprocess.run(["mv", current_recording_file, save_path], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        add_debug(f"Saved recording to: {save_path}")
                        status_var.set(f"Saved: {os.path.basename(save_path)}")
                        current_recording_file = save_path
                        recording_was_saved = True  # Mark as saved
                    else:
                        status_var.set(f"Save failed: {result.stderr}")
                        print(f"Save error: {result.stderr}", file=sys.stderr)
            else:
                status_var.set("No recording to save")
        except Exception as e:
            status_var.set(f"Save error: {e}")
            print(f"Save error: {e}", file=sys.stderr)

    # Function to handle window close
    def on_closing():
        global recording_process, serial_port
        # Close serial port properly
        if serial_port and serial_port.is_open:
            try:
                serial_port.rts = False
                serial_port.dtr = False
                serial_port.close()
                print("Serial port closed", file=sys.stderr)
            except:
                pass
        if recording_process is not None:
            recording_process.terminate()
            try:
                recording_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                recording_process.kill()
        root.destroy()
    
    # Recording Frame
    misc_frame = tk.LabelFrame(root, text="QSO Recording", padx=10, pady=10, bd=2, relief=tk.GROOVE)
    misc_frame.pack(padx=10, pady=5, fill=tk.X)

    btn_rec = tk.Button(misc_frame, text="REC", width=6, command=toggle_recording)
    btn_rec.pack(side=tk.LEFT, padx=5, anchor=tk.W)
    
    # Store the default button color
    default_btn_bg = btn_rec.cget("background")
    default_btn_fg = btn_rec.cget("foreground")
    
    btn_delete = tk.Button(misc_frame, text="Delete", width=6, command=delete_recording)
    btn_delete.pack(side=tk.LEFT, padx=5)
    
    btn_play = tk.Button(misc_frame, text="Play", width=6, command=play_recording)
    btn_play.pack(side=tk.LEFT, padx=5)
    
    btn_save = tk.Button(misc_frame, text="Save", width=6, command=save_recording)
    btn_save.pack(side=tk.LEFT, padx=5)

    # Voice Keyer Frame
    voice_keyer_frame = tk.LabelFrame(root, text="Voice Keyer", padx=10, pady=10, bd=2, relief=tk.GROOVE)
    voice_keyer_frame.pack(padx=10, pady=5, fill=tk.X)

    # First row - Voice Memory Buttons
    voice_row1 = tk.Frame(voice_keyer_frame)
    voice_row1.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)
    
    lbl_memories = tk.Label(voice_row1, text="Memories:", font=("Arial", 9, "bold"), width=10, anchor=tk.CENTER)
    lbl_memories.pack(side=tk.LEFT, padx=5)
    
    def play_voice_memory_t1():
        try:
            if not serial_port or not serial_port.is_open:
                status_var.set("Serial port not available")
                add_debug("Serial port error")
                return
            
            ptt_status = flrig.rig.get_ptt()
            if ptt_status == 1:
                status_var.set("Already transmitting")
                add_debug("Voice keyer blocked: already transmitting")
                return
            
            # Raise RTS to key the radio
            try:
                serial_port.rts = True
                add_debug("RTS raised for T1")
                time.sleep(0.05)
                
                # Send CI-V command to play T1 memory
                cmd = bytes.fromhex("FEFE94E3280001FD")
                serial_port.write(cmd)
                add_debug("T1 CI-V command sent")
                
                time.sleep(0.05)
                serial_port.rts = False
                add_debug("RTS lowered after command")
            except Exception as e:
                add_debug(f"Serial error: {e}")
                try:
                    serial_port.rts = False
                except:
                    pass
                return
            
            status_var.set("Playing T1")
            add_debug("T1 playing")
            
            # Monitor power meter and stop when done
            def wait_and_stop():
                try:
                    pwrmeter = float(flrig.rig.get_pwrmeter())
                    if pwrmeter == 0:
                        status_var.set("T1 finished")
                        add_debug("T1 finished")
                    else:
                        root.after(100, wait_and_stop)
                except Exception as e:
                    add_debug(f"Monitor error: {e}")
            
            root.after(300, wait_and_stop)
        except Exception as e:
            status_var.set(f"Error: {e}")
            add_debug(f"Voice keyer error: {e}")
    
    btn_n9oh = tk.Button(voice_row1, text=config.get('Voice Keyer Memory', 't1_label', fallback='N9OH'), width=6, command=play_voice_memory_t1)
    btn_n9oh.pack(side=tk.LEFT, padx=5)
    
    def play_voice_memory_t2():
        try:
            if not serial_port or not serial_port.is_open:
                status_var.set("Serial port not available")
                add_debug("Serial port error")
                return
            
            ptt_status = flrig.rig.get_ptt()
            if ptt_status == 1:
                status_var.set("Already transmitting")
                add_debug("Voice keyer blocked: already transmitting")
                return
            
            # Raise RTS to key the radio
            try:
                serial_port.rts = True
                add_debug("RTS raised for T2")
                time.sleep(0.05)
                
                # Send CI-V command to play T2 memory
                cmd = bytes.fromhex("FEFE94E3280002FD")
                serial_port.write(cmd)
                add_debug("T2 CI-V command sent")
                
                time.sleep(0.05)
                serial_port.rts = False
                add_debug("RTS lowered after command")
            except Exception as e:
                add_debug(f"Serial error: {e}")
                try:
                    serial_port.rts = False
                except:
                    pass
                return
            
            status_var.set("Playing T2")
            add_debug("T2 playing")
            
            # Monitor power meter and stop when done
            def wait_and_stop():
                try:
                    pwrmeter = float(flrig.rig.get_pwrmeter())
                    if pwrmeter == 0:
                        status_var.set("T2 finished")
                        add_debug("T2 finished")
                    else:
                        root.after(100, wait_and_stop)
                except Exception as e:
                    add_debug(f"Monitor error: {e}")
            
            root.after(300, wait_and_stop)
        except Exception as e:
            status_var.set(f"Error: {e}")
            add_debug(f"Voice keyer error: {e}")
    
    btn_t2 = tk.Button(voice_row1, text=config.get('Voice Keyer Memory', 't2_label', fallback='59 FL'), width=6, command=play_voice_memory_t2)
    btn_t2.pack(side=tk.LEFT, padx=5)
    
    btn_t3 = tk.Button(voice_row1, text=config.get('Voice Keyer Memory', 't3_label', fallback='T3'), width=6, state=tk.DISABLED)
    btn_t3.pack(side=tk.LEFT, padx=5)
    
    btn_t4 = tk.Button(voice_row1, text=config.get('Voice Keyer Memory', 't4_label', fallback='T4'), width=6, state=tk.DISABLED)
    btn_t4.pack(side=tk.LEFT, padx=5)

    # Second row - TTS Buttons
    voice_row2 = tk.Frame(voice_keyer_frame)
    voice_row2.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)
    
    lbl_tts = tk.Label(voice_row2, text="Piper TTS:", font=("Arial", 9, "bold"), width=10, anchor=tk.CENTER)
    lbl_tts.pack(side=tk.LEFT, padx=5)
    
    def play_tts_n9oh():
        def tts_thread():
            try:
                if not serial_port or not serial_port.is_open:
                    add_debug("Serial port not available")
                    status_var.set("Serial port error")
                    return
                
                wav_file = "/tmp/tts_n9oh.wav"
                
                # Check if pre-generated file exists
                if not os.path.exists(wav_file):
                    add_debug("TTS file not ready yet, waiting...")
                    status_var.set("Waiting for TTS generation...")
                    # Wait up to 5 seconds for file
                    for i in range(50):
                        if os.path.exists(wav_file):
                            break
                        time.sleep(0.1)
                    if not os.path.exists(wav_file):
                        add_debug("ERROR: TTS file still not available")
                        status_var.set("TTS generation failed")
                        return
                
                add_debug(f"Using pre-generated TTS audio: {wav_file}")
                
                # Save current mode and switch to DATA version of current mode
                original_mode = None
                try:
                    original_mode = flrig.rig.get_mode()
                    add_debug(f"Current mode: {original_mode}")
                    # Switch to DATA version of current mode (USB->USB-D, LSB->LSB-D, etc)
                    if "-D" not in original_mode:
                        data_mode = original_mode + "-D"
                    else:
                        data_mode = original_mode
                    flrig.rig.set_mode(data_mode)
                    add_debug(f"Switched to {data_mode} mode")
                    time.sleep(0.2)
                except Exception as e:
                    add_debug(f"Mode switch error: {e}")
                
                add_debug("Raising RTS to key radio...")
                
                # Raise RTS to key the radio
                try:
                    serial_port.rts = True
                    add_debug("RTS raised for TTS playback")
                except Exception as e:
                    add_debug(f"RTS error: {e}")
                    status_var.set("RTS control failed")
                    return
                
                # Play the generated audio with paplay
                add_debug(f"Playing: paplay {wav_file}")
                paplay_process = subprocess.Popen(
                    ["paplay", wav_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
                
                paplay_output, paplay_error = paplay_process.communicate()
                if paplay_process.returncode != 0:
                    add_debug(f"paplay error: {paplay_error.decode()}")
                
                add_debug("TTS playback finished, lowering RTS...")
                
                # Lower RTS after audio finishes
                try:
                    serial_port.rts = False
                    add_debug("RTS lowered after TTS playback")
                except Exception as e:
                    add_debug(f"RTS lower error: {e}")
                
                # Switch back to original mode (non-DATA version)
                if original_mode:
                    try:
                        restore_mode = original_mode.replace("-D", "")
                        flrig.rig.set_mode(restore_mode)
                        add_debug(f"Restored to {restore_mode} mode after TTS playback")
                        time.sleep(0.1)
                    except Exception as e:
                        add_debug(f"Mode restore error: {e}")
                
                status_var.set("TTS N9OH finished")
            except Exception as e:
                add_debug(f"TTS error: {e}")
                status_var.set(f"TTS error: {e}")
                try:
                    serial_port.rts = False
                except:
                    pass
        
        status_var.set("Playing TTS N9OH...")
        tts_thread_obj = threading.Thread(target=tts_thread, daemon=True)
        tts_thread_obj.start()
    
    btn_tts_n9oh = tk.Button(voice_row2, text=config.get('Piper TTS', 'button1_label', fallback='N9OH'), width=6, command=play_tts_n9oh)
    btn_tts_n9oh.pack(side=tk.LEFT, padx=5)
    
    def play_tts_tu59():
        def tts_thread():
            try:
                if not serial_port or not serial_port.is_open:
                    add_debug("Serial port not available")
                    status_var.set("Serial port error")
                    return
                
                wav_file = "/tmp/tts_tu59.wav"
                
                # Check if pre-generated file exists
                if not os.path.exists(wav_file):
                    add_debug("TTS file not ready yet, waiting...")
                    status_var.set("Waiting for TTS generation...")
                    # Wait up to 5 seconds for file
                    for i in range(50):
                        if os.path.exists(wav_file):
                            break
                        time.sleep(0.1)
                    if not os.path.exists(wav_file):
                        add_debug("ERROR: TTS file still not available")
                        status_var.set("TTS generation failed")
                        return
                
                add_debug(f"Using pre-generated TTS audio: {wav_file}")
                
                # Save current mode and switch to DATA version of current mode
                original_mode = None
                try:
                    original_mode = flrig.rig.get_mode()
                    add_debug(f"Current mode: {original_mode}")
                    # Switch to DATA version of current mode (USB->USB-D, LSB->LSB-D, etc)
                    if "-D" not in original_mode:
                        data_mode = original_mode + "-D"
                    else:
                        data_mode = original_mode
                    flrig.rig.set_mode(data_mode)
                    add_debug(f"Switched to {data_mode} mode")
                    time.sleep(0.2)
                except Exception as e:
                    add_debug(f"Mode switch error: {e}")
                
                add_debug("Raising RTS to key radio...")
                
                # Raise RTS to key the radio
                try:
                    serial_port.rts = True
                    add_debug("RTS raised for TTS playback")
                except Exception as e:
                    add_debug(f"RTS error: {e}")
                    status_var.set("RTS control failed")
                    return
                
                # Play the generated audio with paplay
                add_debug(f"Playing: paplay {wav_file}")
                paplay_process = subprocess.Popen(
                    ["paplay", wav_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
                
                paplay_output, paplay_error = paplay_process.communicate()
                if paplay_process.returncode != 0:
                    add_debug(f"paplay error: {paplay_error.decode()}")
                
                add_debug("TTS playback finished, lowering RTS...")
                
                # Lower RTS after audio finishes
                try:
                    serial_port.rts = False
                    add_debug("RTS lowered after TTS playback")
                except Exception as e:
                    add_debug(f"RTS lower error: {e}")
                
                # Switch back to original mode (non-DATA version)
                if original_mode:
                    try:
                        restore_mode = original_mode.replace("-D", "")
                        flrig.rig.set_mode(restore_mode)
                        add_debug(f"Restored to {restore_mode} mode after TTS playback")
                        time.sleep(0.1)
                    except Exception as e:
                        add_debug(f"Mode restore error: {e}")
                
                status_var.set("TTS TU 59 finished")
            except Exception as e:
                add_debug(f"TTS error: {e}")
                status_var.set(f"TTS error: {e}")
                try:
                    serial_port.rts = False
                except:
                    pass
        
        status_var.set("Playing TTS TU 59...")
        tts_thread_obj = threading.Thread(target=tts_thread, daemon=True)
        tts_thread_obj.start()
    
    btn_tts_tu59 = tk.Button(voice_row2, text=config.get('Piper TTS', 'button2_label', fallback='TU 59'), width=6, command=play_tts_tu59)
    btn_tts_tu59.pack(side=tk.LEFT, padx=5)
    
    def play_tts_73():
        def tts_thread():
            try:
                if not serial_port or not serial_port.is_open:
                    add_debug("Serial port not available")
                    status_var.set("Serial port error")
                    return
                
                wav_file = "/tmp/tts_73.wav"
                pitched_file = "/tmp/tts_73_pitched.wav"
                
                # Check if pre-generated file exists
                if not os.path.exists(wav_file):
                    add_debug("TTS file not ready yet, waiting...")
                    status_var.set("Waiting for TTS generation...")
                    # Wait up to 5 seconds for file
                    for i in range(50):
                        if os.path.exists(wav_file):
                            break
                        time.sleep(0.1)
                    if not os.path.exists(wav_file):
                        add_debug("ERROR: TTS file still not available")
                        status_var.set("TTS generation failed")
                        return
                
                add_debug(f"Using pre-generated TTS audio: {wav_file}")
                
                # Apply sox pitch shift if configured
                button3_pitch = config.get('Piper TTS', 'button3_pitch', fallback='150')
                try:
                    if button3_pitch and button3_pitch != "0":
                        sox_cmd = ["sox", wav_file, pitched_file, "pitch", button3_pitch]
                        result = subprocess.run(sox_cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            add_debug(f"Applied pitch shift ({button3_pitch} cents) to {pitched_file}")
                            playback_file = pitched_file
                        else:
                            add_debug(f"Sox pitch error: {result.stderr}, using original file")
                            playback_file = wav_file
                    else:
                        playback_file = wav_file
                except Exception as e:
                    add_debug(f"Sox error: {e}, using original file")
                    playback_file = wav_file
                
                # Save current mode and switch to DATA version of current mode
                original_mode = None
                try:
                    original_mode = flrig.rig.get_mode()
                    add_debug(f"Current mode: {original_mode}")
                    # Switch to DATA version of current mode (USB->USB-D, LSB->LSB-D, etc)
                    if "-D" not in original_mode:
                        data_mode = original_mode + "-D"
                    else:
                        data_mode = original_mode
                    flrig.rig.set_mode(data_mode)
                    add_debug(f"Switched to {data_mode} mode")
                    time.sleep(0.2)
                except Exception as e:
                    add_debug(f"Mode switch error: {e}")
                
                add_debug("Raising RTS to key radio...")
                
                # Raise RTS to key the radio
                try:
                    serial_port.rts = True
                    add_debug("RTS raised for TTS playback")
                except Exception as e:
                    add_debug(f"RTS error: {e}")
                    status_var.set("RTS control failed")
                    return
                
                # Play the generated audio with paplay
                add_debug(f"Playing: paplay {playback_file}")
                paplay_process = subprocess.Popen(
                    ["paplay", playback_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
                
                paplay_output, paplay_error = paplay_process.communicate()
                if paplay_process.returncode != 0:
                    add_debug(f"paplay error: {paplay_error.decode()}")
                
                add_debug("TTS playback finished, lowering RTS...")
                
                # Lower RTS after audio finishes
                try:
                    serial_port.rts = False
                    add_debug("RTS lowered after TTS playback")
                except Exception as e:
                    add_debug(f"RTS lower error: {e}")
                
                # Switch back to original mode (non-DATA version)
                if original_mode:
                    try:
                        restore_mode = original_mode.replace("-D", "")
                        flrig.rig.set_mode(restore_mode)
                        add_debug(f"Restored to {restore_mode} mode after TTS playback")
                        time.sleep(0.1)
                    except Exception as e:
                        add_debug(f"Mode restore error: {e}")
                
                status_var.set("TTS 73 finished")
            except Exception as e:
                add_debug(f"TTS error: {e}")
                status_var.set(f"TTS error: {e}")
                try:
                    serial_port.rts = False
                except:
                    pass
        
        status_var.set("Playing TTS 73...")
        tts_thread_obj = threading.Thread(target=tts_thread, daemon=True)
        tts_thread_obj.start()
    
    btn_tts_73 = tk.Button(voice_row2, text=config.get('Piper TTS', 'button3_label', fallback='73'), width=6, command=play_tts_73)
    btn_tts_73.pack(side=tk.LEFT, padx=5)

    # Debug section (collapsible)
    debug_visible = False
    original_geometry = None
    
    def toggle_debug():
        global debug_visible, original_geometry
        if debug_visible:
            debug_frame.pack_forget()
            btn_debug_toggle.config(text="▶ Show Debug")
            debug_visible = False
            # Restore original window size
            if original_geometry:
                root.geometry(original_geometry)
        else:
            # Save current window size before expanding
            root.update_idletasks()
            original_geometry = root.geometry()
            debug_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
            btn_debug_toggle.config(text="▼ Hide Debug")
            debug_visible = True
            # Expand window to show debug section
            root.update_idletasks()
            width = root.winfo_width()
            height = root.winfo_height() + 250  # Add space for debug section
            root.geometry(f"{width}x{height}")
    
    # Toggle button for debug section
    btn_debug_toggle = tk.Button(root, text="▶ Show Debug", command=toggle_debug, 
                                 relief=tk.FLAT, anchor=tk.W, font=("TkDefaultFont", 9))
    btn_debug_toggle.pack(padx=10, pady=(5, 0), fill=tk.X)
    
    # Debug frame (initially hidden)
    debug_frame = tk.Frame(root)
    
    debug_label = tk.Label(debug_frame, text="Debug Output:", anchor=tk.W)
    debug_label.pack(fill=tk.X)
    
    debug_text = scrolledtext.ScrolledText(debug_frame, height=10, width=80, wrap=tk.WORD, 
                                           bg="#f0f0f0", font=("Courier", 9))
    debug_text.pack(fill=tk.BOTH, expand=True)
    
    # Clear debug button
    def clear_debug():
        debug_text.delete(1.0, tk.END)
        add_debug("Debug output cleared")
    
    btn_clear_debug = tk.Button(debug_frame, text="Clear", command=clear_debug)
    btn_clear_debug.pack(pady=(5, 0))

    # Start debug queue processing
    process_debug_queue()
    add_debug("Rig Macros started")

    root.protocol("WM_DELETE_WINDOW", on_closing)
    poll_rig_status()
    root.mainloop()

except Exception as e:
    print(f"Startup error: {e}", file=sys.stderr)
    input("Press Enter to exit...")

