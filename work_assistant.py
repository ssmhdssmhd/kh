#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作助手应用 - 语音自动记录会议要点、智能总结
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
import json
import os
import threading
import time
from pathlib import Path
import re

try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    from nltk.probability import FreqDist
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

DATA_DIR = Path(__file__).parent / "data"
RECORDS_FILE = DATA_DIR / "records.json"
CONFIG_FILE = DATA_DIR / "config.json"


class VoiceRecorder:
    def __init__(self, callback):
        self.callback = callback
        self.is_recording = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.recording_thread = None
        self.text_buffer = []
    
    def start_recording(self):
        if not SPEECH_AVAILABLE:
            raise ImportError("请安装 speech_recognition 库")
        
        self.is_recording = True
        self.text_buffer = []
        
        def record_loop():
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                while self.is_recording:
                    try:
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=15)
                        text = self.recognizer.recognize_google(audio, language='zh-CN')
                        self.text_buffer.append(text)
                        if self.callback:
                            self.callback(text)
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except Exception as e:
                        print(f"语音识别错误: {e}")
                        time.sleep(1)
        
        self.recording_thread = threading.Thread(target=record_loop, daemon=True)
        self.recording_thread.start()
    
    def stop_recording(self):
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
        return "\n".join(self.text_buffer)
    
    def get_buffer(self):
        return "\n".join(self.text_buffer)


class MeetingSummarizer:
    @staticmethod
    def extract_keywords(text, num_keywords=10):
        if not text.strip():
            return []
        
        try:
            if NLTK_AVAILABLE:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                
                tokens = word_tokenize(text)
                stop_words = set(stopwords.words('chinese'))
                filtered_tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
                
                freq_dist = FreqDist(filtered_tokens)
                keywords = [word for word, freq in freq_dist.most_common(num_keywords)]
                return keywords
            else:
                return MeetingSummarizer._simple_keyword_extraction(text, num_keywords)
        except:
            return MeetingSummarizer._simple_keyword_extraction(text, num_keywords)
    
    @staticmethod
    def _simple_keyword_extraction(text, num_keywords=10):
        word_counts = {}
        for word in re.findall(r'[\u4e00-\u9fff]{2,}', text):
            if word not in ['的', '是', '在', '有', '和', '了', '我', '你', '他', '她', '它', '这', '那', '们', '都', '就', '而', '及', '与', '等', '能', '会', '要', '可以', '应该', '必须']:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:num_keywords]]
    
    @staticmethod
    def summarize(text, max_sentences=5):
        if not text.strip():
            return "暂无内容"
        
        sentences = sent_tokenize(text) if NLTK_AVAILABLE else text.split('。')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= max_sentences:
            return text
        
        scores = []
        keywords = set(MeetingSummarizer.extract_keywords(text, 20))
        
        for i, sentence in enumerate(sentences):
            score = 0
            sentence_words = set(re.findall(r'[\u4e00-\u9fff]{2,}', sentence))
            for keyword in keywords:
                if keyword in sentence_words:
                    score += 1
            score += 1 / (1 + i)
            scores.append((i, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        selected_indices = sorted([i for i, score in scores[:max_sentences]])
        
        summary = "。".join([sentences[i] for i in selected_indices])
        if summary and not summary.endswith('。'):
            summary += '。'
        
        return summary
    
    @staticmethod
    def extract_action_items(text):
        patterns = [
            r'(需要|必须|应该|要|得|务必)\s*(做|完成|处理|解决|提交|跟进|落实)\s*([^\。\？\！]+)',
            r'(负责|承担)\s*([^\。\？\！]+)',
            r'(时间|期限|截止)\s*([^\。\？\！]+)',
            r'(下一步|接下来|随后)\s*(做|进行|讨论)\s*([^\。\？\！]+)',
        ]
        
        action_items = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                item = ''.join(str(m) for m in match).strip()
                if item and item not in action_items:
                    action_items.append(item)
        
        return action_items[:10]


class WorkAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("工作助手 - 语音自动记录会议")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        DATA_DIR.mkdir(exist_ok=True)
        
        self.records = self.load_records()
        self.config = self.load_config()
        
        self.reminder_running = True
        self.reminder_thread = None
        
        self.voice_recorder = None
        self.is_recording = False
        self.recording_text = ""
        
        self.create_widgets()
        self.start_reminder_service()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_records(self):
        if RECORDS_FILE.exists():
            try:
                with open(RECORDS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.get_default_records()
        return self.get_default_records()
    
    def get_default_records(self):
        return {
            "meetings": [],
            "works": [],
            "details": [],
            "improvements": []
        }
    
    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"reminders": []}
        return {"reminders": []}
    
    def save_records(self):
        with open(RECORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
    
    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_meeting_tab()
        self.create_work_tab()
        self.create_detail_tab()
        self.create_improvement_tab()
        self.create_reminder_tab()
        
        self.create_status_bar()
    
    def create_meeting_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🎤 会议录音")
        
        toolbar_frame = ttk.Frame(frame)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.recording_status = ttk.Label(toolbar_frame, text="就绪", foreground="green")
        self.recording_status.pack(side=tk.LEFT, padx=5)
        
        self.record_btn = ttk.Button(toolbar_frame, text="🔴 开始录音", command=self.toggle_recording)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar_frame, text="📝 自动总结", command=self.auto_summarize).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="💾 保存记录", command=self.save_meeting).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="🗑️ 清空内容", command=self.clear_meeting).pack(side=tk.LEFT, padx=5)
        
        main_frame = ttk.Frame(frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        left_frame = ttk.LabelFrame(main_frame, text="🎙️ 语音转文字")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.transcribed_text = scrolledtext.ScrolledText(left_frame, width=40, height=25, font=('Arial', 11))
        self.transcribed_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        middle_frame = ttk.LabelFrame(main_frame, text="📊 自动总结")
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.summary_text = scrolledtext.ScrolledText(middle_frame, width=40, height=25, font=('Arial', 11))
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.LabelFrame(main_frame, text="⭐ 重点提取")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.keyword_frame = ttk.LabelFrame(right_frame, text="🔑 关键词")
        self.keyword_frame.pack(fill=tk.X, padx=5, pady=5)
        self.keyword_labels = []
        
        action_frame = ttk.LabelFrame(right_frame, text="✅ 行动项")
        action_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.action_text = scrolledtext.ScrolledText(action_frame, width=35, height=12, font=('Arial', 10))
        self.action_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 会议信息输入
        info_frame = ttk.LabelFrame(frame, text="会议信息")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(info_frame, text="会议主题:").grid(row=0, column=0, padx=5, pady=3, sticky=tk.W)
        self.meeting_title = ttk.Entry(info_frame, width=30)
        self.meeting_title.grid(row=0, column=1, padx=5, pady=3, sticky=tk.W)
        
        ttk.Label(info_frame, text="会议时间:").grid(row=0, column=2, padx=5, pady=3, sticky=tk.W)
        self.meeting_time = ttk.Entry(info_frame, width=20)
        self.meeting_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.meeting_time.grid(row=0, column=3, padx=5, pady=3, sticky=tk.W)
        
        ttk.Label(info_frame, text="参会人员:").grid(row=0, column=4, padx=5, pady=3, sticky=tk.W)
        self.meeting_attendees = ttk.Entry(info_frame, width=25)
        self.meeting_attendees.grid(row=0, column=5, padx=5, pady=3, sticky=tk.W)
        
        # 历史记录列表
        list_frame = ttk.LabelFrame(frame, text="历史会议记录")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("time", "title", "attendees")
        self.meeting_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        self.meeting_tree.heading("time", text="时间")
        self.meeting_tree.heading("title", text="主题")
        self.meeting_tree.heading("attendees", text="参会人员")
        self.meeting_tree.column("time", width=150)
        self.meeting_tree.column("title", width=350)
        self.meeting_tree.column("attendees", width=200)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.meeting_tree.yview)
        self.meeting_tree.configure(yscrollcommand=scrollbar.set)
        
        self.meeting_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.meeting_tree.bind("<<TreeviewSelect>>", self.show_meeting_detail)
        self.meeting_tree.bind("<Double-1>", self.delete_meeting)
        
        self.refresh_meeting_list()
    
    def on_voice_recognized(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.transcribed_text.insert(tk.END, f"[{timestamp}] {text}\n")
        self.transcribed_text.see(tk.END)
        self.recording_text += text + "\n"
        
        if len(self.recording_text) > 50:
            self.auto_summarize()
    
    def toggle_recording(self):
        if not SPEECH_AVAILABLE:
            messagebox.showwarning("警告", "语音识别功能不可用，请安装 speech_recognition 库:\npip install SpeechRecognition pyaudio")
            return
        
        if not self.is_recording:
            try:
                self.voice_recorder = VoiceRecorder(self.on_voice_recognized)
                self.voice_recorder.start_recording()
                self.is_recording = True
                self.record_btn.config(text="⏹️ 停止录音")
                self.recording_status.config(text="录音中...", foreground="red")
                self.recording_text = ""
                messagebox.showinfo("开始录音", "录音已开始，请说话...")
            except Exception as e:
                messagebox.showerror("错误", f"无法启动录音: {str(e)}\n\n可能原因:\n1. 未安装 pyaudio\n2. 麦克风权限问题")
                self.is_recording = False
        else:
            self.is_recording = False
            if self.voice_recorder:
                self.voice_recorder.stop_recording()
            self.record_btn.config(text="🔴 开始录音")
            self.recording_status.config(text="录音结束", foreground="blue")
            
            if self.recording_text.strip():
                self.auto_summarize()
                messagebox.showinfo("录音完成", "语音转文字已完成，已自动生成总结！")
            else:
                messagebox.showinfo("录音完成", "未识别到语音内容")
    
    def auto_summarize(self):
        full_text = self.transcribed_text.get("1.0", tk.END).strip()
        
        if not full_text:
            messagebox.showwarning("警告", "没有内容可以总结")
            return
        
        summary = MeetingSummarizer.summarize(full_text)
        keywords = MeetingSummarizer.extract_keywords(full_text)
        actions = MeetingSummarizer.extract_action_items(full_text)
        
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, summary)
        
        for label in self.keyword_labels:
            label.destroy()
        self.keyword_labels = []
        
        if keywords:
            for keyword in keywords[:8]:
                label = ttk.Label(self.keyword_frame, text=f"● {keyword}", 
                                foreground="#2E7D32", font=('Arial', 10, 'bold'))
                label.pack(side=tk.LEFT, padx=3, pady=2)
                self.keyword_labels.append(label)
        
        self.action_text.delete("1.0", tk.END)
        if actions:
            for i, action in enumerate(actions, 1):
                self.action_text.insert(tk.END, f"{i}. {action}\n")
        else:
            self.action_text.insert(tk.END, "未识别到行动项")
    
    def save_meeting(self):
        title = self.meeting_title.get().strip() or "未命名会议"
        time_str = self.meeting_time.get().strip()
        attendees = self.meeting_attendees.get().strip()
        full_text = self.transcribed_text.get("1.0", tk.END).strip()
        summary = self.summary_text.get("1.0", tk.END).strip()
        
        if not full_text:
            messagebox.showwarning("警告", "请先录音或输入会议内容！")
            return
        
        keyword_labels = []
        for label in self.keyword_labels:
            keyword_labels.append(label.cget("text").replace("● ", ""))
        keywords = ", ".join(keyword_labels)
        
        actions = self.action_text.get("1.0", tk.END).strip()
        
        meeting = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "time": time_str,
            "attendees": attendees,
            "full_text": full_text,
            "summary": summary,
            "keywords": keywords,
            "action_items": actions,
            "created_at": datetime.now().isoformat()
        }
        
        self.records["meetings"].insert(0, meeting)
        self.save_records()
        self.refresh_meeting_list()
        self.clear_meeting()
        messagebox.showinfo("成功", "会议记录已保存！")
    
    def clear_meeting(self):
        self.meeting_title.delete(0, tk.END)
        self.meeting_time.delete(0, tk.END)
        self.meeting_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.meeting_attendees.delete(0, tk.END)
        self.transcribed_text.delete("1.0", tk.END)
        self.summary_text.delete("1.0", tk.END)
        self.action_text.delete("1.0", tk.END)
        for label in self.keyword_labels:
            label.destroy()
        self.keyword_labels = []
        self.recording_text = ""
    
    def refresh_meeting_list(self):
        for item in self.meeting_tree.get_children():
            self.meeting_tree.delete(item)
        
        for meeting in self.records["meetings"]:
            self.meeting_tree.insert("", tk.END, values=(
                meeting.get("time", ""),
                meeting.get("title", ""),
                meeting.get("attendees", "")
            ))
    
    def show_meeting_detail(self, event):
        selection = self.meeting_tree.selection()
        if selection:
            index = self.meeting_tree.index(selection[0])
            if index < len(self.records["meetings"]):
                meeting = self.records["meetings"][index]
                detail_window = tk.Toplevel(self.root)
                detail_window.title(f"会议详情 - {meeting.get('title', '')}")
                detail_window.geometry("800x600")
                
                notebook = ttk.Notebook(detail_window)
                
                full_frame = ttk.Frame(notebook)
                notebook.add(full_frame, text="完整记录")
                full_text = scrolledtext.ScrolledText(full_frame, width=90, height=30)
                full_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                full_text.insert(tk.END, meeting.get("full_text", ""))
                full_text.config(state=tk.DISABLED)
                
                summary_frame = ttk.Frame(notebook)
                notebook.add(summary_frame, text="总结")
                summary_text = scrolledtext.ScrolledText(summary_frame, width=90, height=30)
                summary_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                summary_text.insert(tk.END, f"关键词: {meeting.get('keywords', '')}\n\n"
                                        f"行动项:\n{meeting.get('action_items', '')}\n\n"
                                        f"总结:\n{meeting.get('summary', '')}")
                summary_text.config(state=tk.DISABLED)
                
                notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def delete_meeting(self, event):
        selection = self.meeting_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条会议记录吗？"):
                index = self.meeting_tree.index(selection[0])
                if index < len(self.records["meetings"]):
                    del self.records["meetings"][index]
                    self.save_records()
                    self.refresh_meeting_list()
    
    def create_work_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📝 工作内容")
        
        input_frame = ttk.LabelFrame(frame, text="新增工作记录")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="工作主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.work_title = ttk.Entry(input_frame, width=50)
        self.work_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="工作日期:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.work_date = ttk.Entry(input_frame, width=50)
        self.work_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.work_date.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="工作内容:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.work_content = scrolledtext.ScrolledText(input_frame, width=60, height=8)
        self.work_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="保存记录", command=self.save_work).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_work).pack(side=tk.LEFT, padx=5)
        
        list_frame = ttk.LabelFrame(frame, text="历史工作记录")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("date", "title", "preview")
        self.work_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.work_tree.heading("date", text="日期")
        self.work_tree.heading("title", text="主题")
        self.work_tree.heading("preview", text="内容预览")
        self.work_tree.column("date", width=120)
        self.work_tree.column("title", width=200)
        self.work_tree.column("preview", width=350)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.work_tree.yview)
        self.work_tree.configure(yscrollcommand=scrollbar.set)
        
        self.work_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.work_tree.bind("<<TreeviewSelect>>", self.show_work_detail)
        self.work_tree.bind("<Double-1>", self.delete_work)
        
        self.refresh_work_list()
    
    def save_work(self):
        title = self.work_title.get().strip()
        date = self.work_date.get().strip()
        content = self.work_content.get("1.0", tk.END).strip()
        
        if not title or not content:
            messagebox.showwarning("警告", "请填写工作主题和工作内容！")
            return
        
        work = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "date": date,
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        
        self.records["works"].insert(0, work)
        self.save_records()
        self.refresh_work_list()
        self.clear_work()
        messagebox.showinfo("成功", "工作记录已保存！")
    
    def clear_work(self):
        self.work_title.delete(0, tk.END)
        self.work_date.delete(0, tk.END)
        self.work_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.work_content.delete("1.0", tk.END)
    
    def refresh_work_list(self):
        for item in self.work_tree.get_children():
            self.work_tree.delete(item)
        
        for work in self.records["works"]:
            preview = work.get("content", "")[:50] + "..." if len(work.get("content", "")) > 50 else work.get("content", "")
            self.work_tree.insert("", tk.END, values=(
                work.get("date", ""),
                work.get("title", ""),
                preview
            ))
    
    def show_work_detail(self, event):
        selection = self.work_tree.selection()
        if selection:
            index = self.work_tree.index(selection[0])
            if index < len(self.records["works"]):
                work = self.records["works"][index]
                detail_window = tk.Toplevel(self.root)
                detail_window.title("工作详情")
                detail_window.geometry("600x400")
                
                text = scrolledtext.ScrolledText(detail_window, width=70, height=20)
                text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text.insert(tk.END, f"工作主题: {work.get('title', '')}\n")
                text.insert(tk.END, f"工作日期: {work.get('date', '')}\n")
                text.insert(tk.END, f"\n工作内容:\n{work.get('content', '')}")
                text.config(state=tk.DISABLED)
    
    def delete_work(self, event):
        selection = self.work_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条工作记录吗？"):
                index = self.work_tree.index(selection[0])
                if index < len(self.records["works"]):
                    del self.records["works"][index]
                    self.save_records()
                    self.refresh_work_list()
    
    def create_detail_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔍 工作细节")
        
        input_frame = ttk.LabelFrame(frame, text="新增工作细节")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="细节主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.detail_title = ttk.Entry(input_frame, width=50)
        self.detail_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="记录时间:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.detail_time = ttk.Entry(input_frame, width=50)
        self.detail_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.detail_time.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="详细内容:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.detail_content = scrolledtext.ScrolledText(input_frame, width=60, height=8)
        self.detail_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="保存记录", command=self.save_detail).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_detail).pack(side=tk.LEFT, padx=5)
        
        list_frame = ttk.LabelFrame(frame, text="历史细节记录")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("time", "title", "preview")
        self.detail_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.detail_tree.heading("time", text="时间")
        self.detail_tree.heading("title", text="主题")
        self.detail_tree.heading("preview", text="内容预览")
        self.detail_tree.column("time", width=150)
        self.detail_tree.column("title", width=200)
        self.detail_tree.column("preview", width=320)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.detail_tree.yview)
        self.detail_tree.configure(yscrollcommand=scrollbar.set)
        
        self.detail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.detail_tree.bind("<<TreeviewSelect>>", self.show_detail_detail)
        self.detail_tree.bind("<Double-1>", self.delete_detail)
        
        self.refresh_detail_list()
    
    def save_detail(self):
        title = self.detail_title.get().strip()
        time_str = self.detail_time.get().strip()
        content = self.detail_content.get("1.0", tk.END).strip()
        
        if not title or not content:
            messagebox.showwarning("警告", "请填写细节主题和详细内容！")
            return
        
        detail = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "time": time_str,
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        
        self.records["details"].insert(0, detail)
        self.save_records()
        self.refresh_detail_list()
        self.clear_detail()
        messagebox.showinfo("成功", "工作细节已保存！")
    
    def clear_detail(self):
        self.detail_title.delete(0, tk.END)
        self.detail_time.delete(0, tk.END)
        self.detail_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.detail_content.delete("1.0", tk.END)
    
    def refresh_detail_list(self):
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)
        
        for detail in self.records["details"]:
            preview = detail.get("content", "")[:50] + "..." if len(detail.get("content", "")) > 50 else detail.get("content", "")
            self.detail_tree.insert("", tk.END, values=(
                detail.get("time", ""),
                detail.get("title", ""),
                preview
            ))
    
    def show_detail_detail(self, event):
        selection = self.detail_tree.selection()
        if selection:
            index = self.detail_tree.index(selection[0])
            if index < len(self.records["details"]):
                detail = self.records["details"][index]
                detail_window = tk.Toplevel(self.root)
                detail_window.title("工作细节详情")
                detail_window.geometry("600x400")
                
                text = scrolledtext.ScrolledText(detail_window, width=70, height=20)
                text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text.insert(tk.END, f"细节主题: {detail.get('title', '')}\n")
                text.insert(tk.END, f"记录时间: {detail.get('time', '')}\n")
                text.insert(tk.END, f"\n详细内容:\n{detail.get('content', '')}")
                text.config(state=tk.DISABLED)
    
    def delete_detail(self, event):
        selection = self.detail_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条细节记录吗？"):
                index = self.detail_tree.index(selection[0])
                if index < len(self.records["details"]):
                    del self.records["details"][index]
                    self.save_records()
                    self.refresh_detail_list()
    
    def create_improvement_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💡 改进建议")
        
        input_frame = ttk.LabelFrame(frame, text="新增改进建议")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="改进主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_title = ttk.Entry(input_frame, width=50)
        self.improvement_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="提出日期:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_date = ttk.Entry(input_frame, width=50)
        self.improvement_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.improvement_date.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="改进内容:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.improvement_content = scrolledtext.ScrolledText(input_frame, width=60, height=8)
        self.improvement_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="状态:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_status = ttk.Combobox(input_frame, values=["待处理", "进行中", "已完成"], width=47)
        self.improvement_status.set("待处理")
        self.improvement_status.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="保存记录", command=self.save_improvement).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_improvement).pack(side=tk.LEFT, padx=5)
        
        list_frame = ttk.LabelFrame(frame, text="历史改进记录")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("date", "title", "status", "preview")
        self.improvement_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.improvement_tree.heading("date", text="日期")
        self.improvement_tree.heading("title", text="主题")
        self.improvement_tree.heading("status", text="状态")
        self.improvement_tree.heading("preview", text="内容预览")
        self.improvement_tree.column("date", width=120)
        self.improvement_tree.column("title", width=150)
        self.improvement_tree.column("status", width=80)
        self.improvement_tree.column("preview", width=320)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.improvement_tree.yview)
        self.improvement_tree.configure(yscrollcommand=scrollbar.set)
        
        self.improvement_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.improvement_tree.bind("<<TreeviewSelect>>", self.show_improvement_detail)
        self.improvement_tree.bind("<Double-1>", self.delete_improvement)
        
        self.refresh_improvement_list()
    
    def save_improvement(self):
        title = self.improvement_title.get().strip()
        date = self.improvement_date.get().strip()
        content = self.improvement_content.get("1.0", tk.END).strip()
        status = self.improvement_status.get().strip()
        
        if not title or not content:
            messagebox.showwarning("警告", "请填写改进主题和改进内容！")
            return
        
        improvement = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "date": date,
            "content": content,
            "status": status,
            "created_at": datetime.now().isoformat()
        }
        
        self.records["improvements"].insert(0, improvement)
        self.save_records()
        self.refresh_improvement_list()
        self.clear_improvement()
        messagebox.showinfo("成功", "改进建议已保存！")
    
    def clear_improvement(self):
        self.improvement_title.delete(0, tk.END)
        self.improvement_date.delete(0, tk.END)
        self.improvement_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.improvement_content.delete("1.0", tk.END)
        self.improvement_status.set("待处理")
    
    def refresh_improvement_list(self):
        for item in self.improvement_tree.get_children():
            self.improvement_tree.delete(item)
        
        for improvement in self.records["improvements"]:
            preview = improvement.get("content", "")[:50] + "..." if len(improvement.get("content", "")) > 50 else improvement.get("content", "")
            self.improvement_tree.insert("", tk.END, values=(
                improvement.get("date", ""),
                improvement.get("title", ""),
                improvement.get("status", ""),
                preview
            ))
    
    def show_improvement_detail(self, event):
        selection = self.improvement_tree.selection()
        if selection:
            index = self.improvement_tree.index(selection[0])
            if index < len(self.records["improvements"]):
                improvement = self.records["improvements"][index]
                detail_window = tk.Toplevel(self.root)
                detail_window.title("改进建议详情")
                detail_window.geometry("600x400")
                
                text = scrolledtext.ScrolledText(detail_window, width=70, height=20)
                text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text.insert(tk.END, f"改进主题: {improvement.get('title', '')}\n")
                text.insert(tk.END, f"提出日期: {improvement.get('date', '')}\n")
                text.insert(tk.END, f"状态: {improvement.get('status', '')}\n")
                text.insert(tk.END, f"\n改进内容:\n{improvement.get('content', '')}")
                text.config(state=tk.DISABLED)
    
    def delete_improvement(self, event):
        selection = self.improvement_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条改进记录吗？"):
                index = self.improvement_tree.index(selection[0])
                if index < len(self.records["improvements"]):
                    del self.records["improvements"][index]
                    self.save_records()
                    self.refresh_improvement_list()
    
    def create_reminder_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⏰ 会议提醒")
        
        input_frame = ttk.LabelFrame(frame, text="新增会议提醒")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="会议主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_title = ttk.Entry(input_frame, width=50)
        self.reminder_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="会议时间:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_time = ttk.Entry(input_frame, width=50)
        self.reminder_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.reminder_time.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="提前提醒:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_advance = ttk.Combobox(input_frame, values=["5分钟", "10分钟", "15分钟", "30分钟", "1小时"], width=47)
        self.reminder_advance.set("15分钟")
        self.reminder_advance.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(input_frame, text="备注:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_note = ttk.Entry(input_frame, width=50)
        self.reminder_note.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="添加提醒", command=self.add_reminder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_reminder).pack(side=tk.LEFT, padx=5)
        
        list_frame = ttk.LabelFrame(frame, text="已设置的提醒")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("time", "title", "advance", "note")
        self.reminder_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.reminder_tree.heading("time", text="会议时间")
        self.reminder_tree.heading("title", text="主题")
        self.reminder_tree.heading("advance", text="提前提醒")
        self.reminder_tree.heading("note", text="备注")
        self.reminder_tree.column("time", width=150)
        self.reminder_tree.column("title", width=200)
        self.reminder_tree.column("advance", width=100)
        self.reminder_tree.column("note", width=200)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.reminder_tree.yview)
        self.reminder_tree.configure(yscrollcommand=scrollbar.set)
        
        self.reminder_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.reminder_tree.bind("<Double-1>", self.delete_reminder)
        
        self.refresh_reminder_list()
    
    def add_reminder(self):
        title = self.reminder_title.get().strip()
        time_str = self.reminder_time.get().strip()
        advance = self.reminder_advance.get().strip()
        note = self.reminder_note.get().strip()
        
        if not title or not time_str:
            messagebox.showwarning("警告", "请填写会议主题和会议时间！")
            return
        
        try:
            meeting_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except:
            messagebox.showwarning("警告", "时间格式错误，请使用 YYYY-MM-DD HH:MM 格式！")
            return
        
        reminder = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "time": time_str,
            "advance": advance,
            "note": note,
            "notified": False
        }
        
        self.config["reminders"].append(reminder)
        self.save_config()
        self.refresh_reminder_list()
        self.clear_reminder()
        messagebox.showinfo("成功", "会议提醒已添加！")
    
    def clear_reminder(self):
        self.reminder_title.delete(0, tk.END)
        self.reminder_time.delete(0, tk.END)
        self.reminder_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.reminder_note.delete(0, tk.END)
    
    def refresh_reminder_list(self):
        for item in self.reminder_tree.get_children():
            self.reminder_tree.delete(item)
        
        for reminder in self.config["reminders"]:
            self.reminder_tree.insert("", tk.END, values=(
                reminder.get("time", ""),
                reminder.get("title", ""),
                reminder.get("advance", ""),
                reminder.get("note", "")
            ))
    
    def delete_reminder(self, event):
        selection = self.reminder_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这个提醒吗？"):
                index = self.reminder_tree.index(selection[0])
                if index < len(self.config["reminders"]):
                    del self.config["reminders"][index]
                    self.save_config()
                    self.refresh_reminder_list()
    
    def start_reminder_service(self):
        def check_reminders():
            while self.reminder_running:
                try:
                    now = datetime.now()
                    for reminder in self.config["reminders"]:
                        if not reminder.get("notified", False):
                            try:
                                meeting_time = datetime.strptime(reminder["time"], "%Y-%m-%d %H:%M")
                                advance_str = reminder.get("advance", "15分钟")
                                advance_minutes = int(advance_str.replace("分钟", "").replace("小时", ""))
                                if "小时" in advance_str:
                                    advance_minutes *= 60
                                
                                remind_time = meeting_time - timedelta(minutes=advance_minutes)
                                
                                if now >= remind_time:
                                    self.show_reminder_popup(reminder)
                                    reminder["notified"] = True
                                    self.save_config()
                            except Exception as e:
                                print(f"提醒检查错误: {e}")
                    
                    time.sleep(30)
                except Exception as e:
                    print(f"提醒服务错误: {e}")
                    time.sleep(30)
        
        self.reminder_thread = threading.Thread(target=check_reminders, daemon=True)
        self.reminder_thread.start()
    
    def show_reminder_popup(self, reminder):
        def popup():
            messagebox.showinfo(
                "会议提醒",
                f"会议即将开始！\n\n"
                f"主题: {reminder.get('title', '')}\n"
                f"时间: {reminder.get('time', '')}\n"
                f"备注: {reminder.get('note', '')}"
            )
        
        self.root.after(0, popup)
    
    def create_status_bar(self):
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)
        
        ttk.Label(status_frame, text=f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}").pack(side=tk.RIGHT)
    
    def on_closing(self):
        if self.is_recording and self.voice_recorder:
            self.voice_recorder.stop_recording()
        self.reminder_running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = WorkAssistant(root)
    root.mainloop()


if __name__ == "__main__":
    main()