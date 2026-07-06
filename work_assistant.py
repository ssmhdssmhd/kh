#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作助手应用 - 专业开会模式，实时语音识别，精准文字转换
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont
from datetime import datetime, timedelta
import json
import os
import threading
import time
from pathlib import Path
import re
import sys

try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

DATA_DIR = Path(__file__).parent / "data"
RECORDS_FILE = DATA_DIR / "records.json"
CONFIG_FILE = DATA_DIR / "config.json"


class TextProcessor:
    """文本后处理器 - 提升识别准确率和美观度"""
    
    @staticmethod
    def auto_punctuate(text):
        """自动添加标点符号"""
        if not text.strip():
            return text
        
        text = text.strip()
        
        patterns = [
            (r'(今天|明天|昨天|后天|前天|上周|下周|本月|下月|今年|明年)\s*', r'\1，'),
            (r'(首先|其次|然后|接着|最后|另外|此外|同时|因此|所以)', r'\1，'),
            (r'(好的|好的好的|明白了|了解了|知道了|收到|对的|是的|没错)', r'\1。'),
            (r'(谢谢|感谢|非常感谢|辛苦|辛苦了)', r'\1。'),
            (r'(那么|既然这样|这样的话|所以说|也就是说)', r'\1，'),
            (r'(等等|之类的|什么的|等等吧|等等啊)', r'\1。'),
            (r'(吧|呢|啊|吗|嘛|啦|呀|哦|哈|嘿|喂|哎)$', r'\1？'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        
        if text and text[-1] not in '。！？，、；：':
            text += '。'
        
        text = re.sub(r'[，。！？、；：]{2,}', lambda m: m.group(0)[-1], text)
        
        return text
    
    @staticmethod
    def correct_common_errors(text):
        """纠正常见的语音识别错误"""
        corrections = {
            '的话的': '的话',
            '然后然后': '然后',
            '就是就是': '就是',
            '这个这个': '这个',
            '那个那个': '那个',
            '因为因为': '因为',
            '所以所以': '所以',
            '但是但是': '但是',
            '的的': '的',
            '了了': '了',
            '着着': '着',
            '在在': '在',
            '是是': '是',
            '有有': '有',
            '我我': '我',
            '你你': '你',
            '他他': '他',
            '我们我们': '我们',
            '你们你们': '你们',
            '他们他们': '他们',
            '大家大家': '大家',
            '问题问题': '问题',
            '事情事情': '事情',
            '东西东西': '东西',
            '时间时间': '时间',
            '现在现在': '现在',
            '今天今天': '今天',
            '明天明天': '明天',
            '工作工作': '工作',
            '项目项目': '项目',
            '任务任务': '任务',
            '计划计划': '计划',
            '进度进度': '进度',
            '报告报告': '报告',
            '会议会议': '会议',
            '讨论讨论': '讨论',
            '沟通沟通': '沟通',
            '协调协调': '协调',
            '安排安排': '安排',
            '落实落实': '落实',
            '执行执行': '执行',
            '完成完成': '完成',
            '准备准备': '准备',
            '开始开始': '开始',
            '结束结束': '结束',
            '进行进行': '进行',
        }
        
        for wrong, right in corrections.items():
            text = text.replace(wrong, right)
        
        return text
    
    @staticmethod
    def format_paragraph(text):
        """格式化段落，使其更美观易读"""
        if not text.strip():
            return text
        
        sentences = re.split(r'([。！？])', text)
        result = []
        current_paragraph = ''
        
        for i, part in enumerate(sentences):
            if part in '。！？':
                current_paragraph += part
                if len(current_paragraph) > 50:
                    result.append(current_paragraph.strip())
                    current_paragraph = ''
            else:
                current_paragraph += part
        
        if current_paragraph.strip():
            result.append(current_paragraph.strip())
        
        return '\n\n'.join(result)
    
    @staticmethod
    def remove_filler_words(text):
        """去除语气词和填充词"""
        fillers = [
            '嗯', '呃', '啊', '哦', '哈', '嘿', '喂', '哎', '唉',
            '那个', '这个', '就是说', '怎么说呢', '然后呢', '就是',
            '其实呢', '说白了', '简单来说', '总的来说',
        ]
        
        for filler in fillers:
            text = re.sub(rf'{filler}[，。！？、]?', '', text)
        
        return text
    
    @staticmethod
    def process_text(text, remove_fillers=False):
        """完整的文本处理流程"""
        if not text.strip():
            return text
        
        text = TextProcessor.correct_common_errors(text)
        text = TextProcessor.auto_punctuate(text)
        if remove_fillers:
            text = TextProcessor.remove_filler_words(text)
        text = TextProcessor.correct_common_errors(text)
        
        return text


class SubtitleDisplay:
    """实时字幕显示组件"""
    
    def __init__(self, parent, max_lines=5):
        self.parent = parent
        self.max_lines = max_lines
        self.lines = []
        
        self.frame = tk.Frame(parent, bg='#1a1a2e')
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        self.subtitle_frame = tk.Frame(self.frame, bg='#1a1a2e')
        self.subtitle_frame.pack(fill=tk.X, pady=20)
        
        self.labels = []
        for i in range(max_lines):
            label = tk.Label(
                self.subtitle_frame,
                text='',
                font=('Microsoft YaHei UI', 18, 'bold'),
                fg='white',
                bg='#1a1a2e',
                wraplength=900,
                justify='center'
            )
            label.pack(pady=3)
            self.labels.append(label)
    
    def add_line(self, text):
        """添加一行字幕"""
        self.lines.append(text)
        if len(self.lines) > self.max_lines:
            self.lines.pop(0)
        
        for i, label in enumerate(self.labels):
            if i < len(self.lines):
                label.config(text=self.lines[len(self.lines) - 1 - i])
            else:
                label.config(text='')
    
    def clear(self):
        """清空字幕"""
        self.lines = []
        for label in self.labels:
            label.config(text='')


class MeetingRecorder:
    """专业会议录音器"""
    
    def __init__(self, text_callback, subtitle_callback):
        self.text_callback = text_callback
        self.subtitle_callback = subtitle_callback
        self.is_recording = False
        self.recognizer = None
        self.microphone = None
        self.recording_thread = None
        self.full_text = []
        self.current_text = ''
        
        if SPEECH_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.recognizer.phrase_threshold = 0.3
            self.recognizer.non_speaking_duration = 0.5
            
            try:
                self.microphone = sr.Microphone()
            except Exception as e:
                print(f"麦克风初始化失败: {e}")
                self.microphone = None
    
    def start_recording(self):
        """开始录音"""
        if not SPEECH_AVAILABLE or not self.microphone:
            raise Exception("语音识别不可用，请安装 SpeechRecognition 和 pyaudio")
        
        self.is_recording = True
        self.full_text = []
        self.current_text = ''
        
        def record_loop():
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                while self.is_recording:
                    try:
                        audio = self.recognizer.listen(
                            source,
                            timeout=5,
                            phrase_time_limit=10
                        )
                        
                        try:
                            text = self.recognizer.recognize_google(
                                audio,
                                language='zh-CN',
                                show_all=False
                            )
                            
                            if text and len(text.strip()) > 0:
                                processed_text = TextProcessor.process_text(text.strip())
                                
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                self.full_text.append({
                                    'time': timestamp,
                                    'text': text.strip(),
                                    'processed': processed_text
                                })
                                
                                if self.text_callback:
                                    self.text_callback(timestamp, text.strip(), processed_text)
                                
                                if self.subtitle_callback:
                                    self.subtitle_callback(processed_text)
                        
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError as e:
                            print(f"API请求错误: {e}")
                            time.sleep(2)
                        except Exception as e:
                            print(f"识别错误: {e}")
                            time.sleep(1)
                            
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        print(f"监听错误: {e}")
                        time.sleep(1)
                        if not self.is_recording:
                            break
        
        self.recording_thread = threading.Thread(target=record_loop, daemon=True)
        self.recording_thread.start()
    
    def stop_recording(self):
        """停止录音"""
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=3)
        return self.get_full_text()
    
    def get_full_text(self):
        """获取完整文本"""
        return self.full_text
    
    def get_processed_text(self):
        """获取处理后的文本"""
        return '\n'.join([item['processed'] for item in self.full_text])
    
    def get_raw_text(self):
        """获取原始文本"""
        return '\n'.join([item['text'] for item in self.full_text])


class MeetingSummarizer:
    """会议总结器"""
    
    @staticmethod
    def extract_keywords(text, num_keywords=15):
        if not text.strip():
            return []
        
        try:
            if NLTK_AVAILABLE:
                nltk.download('punkt', quiet=True)
                tokens = nltk.word_tokenize(text)
                stop_words = set(['的', '是', '在', '有', '和', '了', '我', '你', '他', '她', '它', 
                                  '这', '那', '们', '都', '就', '而', '及', '与', '等', '能', 
                                  '会', '要', '可以', '应该', '必须', '一个', '我们', '你们',
                                  '他们', '因为', '所以', '但是', '然后', '就是', '这个', '那个'])
                filtered_tokens = [token for token in tokens 
                                   if len(token) >= 2 and token not in stop_words and '\u4e00' <= token[0] <= '\u9fff']
                
                freq_dist = nltk.FreqDist(filtered_tokens)
                keywords = [word for word, freq in freq_dist.most_common(num_keywords)]
                return keywords
        except:
            pass
        
        return MeetingSummarizer._simple_keyword_extraction(text, num_keywords)
    
    @staticmethod
    def _simple_keyword_extraction(text, num_keywords=15):
        word_counts = {}
        stop_words = {'的', '是', '在', '有', '和', '了', '我', '你', '他', '她', '它', 
                      '这', '那', '们', '都', '就', '而', '及', '与', '等', '能', 
                      '会', '要', '可以', '应该', '必须', '一个', '我们', '你们',
                      '他们', '因为', '所以', '但是', '然后', '就是', '这个', '那个'}
        
        for word in re.findall(r'[\u4e00-\u9fff]{2,}', text):
            if word not in stop_words:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:num_keywords]]
    
    @staticmethod
    def summarize(text, max_sentences=8):
        if not text.strip():
            return "暂无内容"
        
        sentences = re.split(r'([。！？])', text)
        result = []
        current = ''
        
        for part in sentences:
            if part in '。！？':
                current += part
                if current.strip():
                    result.append(current.strip())
                current = ''
            else:
                current += part
        
        if current.strip():
            result.append(current.strip())
        
        if len(result) <= max_sentences:
            return text
        
        keywords = set(MeetingSummarizer.extract_keywords(text, 20))
        
        scores = []
        for i, sentence in enumerate(result):
            score = 0
            sentence_words = set(re.findall(r'[\u4e00-\u9fff]{2,}', sentence))
            for keyword in keywords:
                if keyword in sentence_words:
                    score += 1
            
            position_bonus = 1.0 / (1.0 + i * 0.5)
            score += position_bonus
            
            length = len(sentence)
            if 20 <= length <= 100:
                score += 0.5
            
            scores.append((i, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        selected_indices = sorted([i for i, score in scores[:max_sentences]])
        
        summary = ''.join([result[i] for i in selected_indices])
        return summary
    
    @staticmethod
    def extract_action_items(text):
        patterns = [
            (r'(需要|必须|应该|得|务必|一定要)\s*(做|完成|处理|解决|提交|跟进|落实|准备|讨论|确认)\s*([^。！？\n]+)', '需要'),
            (r'(负责|承担|主导|牵头)\s*([^。！？\n]+)', '负责'),
            (r'(截止|限期|最晚|最迟)\s*([^。！？\n]+)', '时间'),
            (r'(下一步|接下来|随后|之后)\s*(要|做|进行|讨论|考虑)\s*([^。！？\n]+)', '下一步'),
            (r'(希望|期望|期待|要求)\s*([^。！？\n]+)', '期望'),
            (r'(注意|关注|重视|留意)\s*([^。！？\n]+)', '注意'),
        ]
        
        action_items = []
        for pattern, category in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                item = ''.join(str(m) for m in match).strip()
                if item and len(item) > 3 and item not in [a['text'] for a in action_items]:
                    action_items.append({
                        'text': item,
                        'category': category
                    })
        
        return action_items[:15]


class WorkAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("工作助手 - 专业开会模式")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        self.root.configure(bg='#f0f2f5')
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#f0f2f5', tabposition='n')
        style.configure('TNotebook.Tab', padding=[20, 10], font=('Microsoft YaHei UI', 10))
        style.map('TNotebook.Tab', background=[('selected', '#1890ff')], foreground=[('selected', 'white')])
        
        DATA_DIR.mkdir(exist_ok=True)
        
        self.records = self.load_records()
        self.config = self.load_config()
        
        self.reminder_running = True
        self.reminder_thread = None
        
        self.meeting_recorder = None
        self.is_meeting_mode = False
        self.meeting_start_time = None
        
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
        
        self.create_meeting_mode_tab()
        self.create_meeting_history_tab()
        self.create_work_tab()
        self.create_detail_tab()
        self.create_improvement_tab()
        self.create_reminder_tab()
    
    def create_meeting_mode_tab(self):
        """创建专业开会模式标签页"""
        frame = tk.Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="🎯 开会模式")
        
        # 顶部控制栏
        control_frame = tk.Frame(frame, bg='white', height=70)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        control_frame.pack_propagate(False)
        
        # 会议主题输入
        tk.Label(control_frame, text="会议主题:", font=('Microsoft YaHei UI', 11), 
                bg='white', fg='#333').pack(side=tk.LEFT, padx=10, pady=20)
        self.meeting_theme = tk.Entry(control_frame, width=30, font=('Microsoft YaHei UI', 11),
                                      relief=tk.FLAT, bg='#f6f6f6')
        self.meeting_theme.pack(side=tk.LEFT, padx=5, pady=20, ipady=5)
        
        # 参会人员
        tk.Label(control_frame, text="参会人员:", font=('Microsoft YaHei UI', 11), 
                bg='white', fg='#333').pack(side=tk.LEFT, padx=10, pady=20)
        self.meeting_attendees_input = tk.Entry(control_frame, width=25, font=('Microsoft YaHei UI', 11),
                                                relief=tk.FLAT, bg='#f6f6f6')
        self.meeting_attendees_input.pack(side=tk.LEFT, padx=5, pady=20, ipady=5)
        
        # 状态标签
        self.meeting_status = tk.Label(control_frame, text="● 待机", 
                                      font=('Microsoft YaHei UI', 12, 'bold'),
                                      bg='white', fg='#999')
        self.meeting_status.pack(side=tk.RIGHT, padx=15, pady=20)
        
        # 开始/停止按钮
        self.start_meeting_btn = tk.Button(
            control_frame, text="🎙️ 开始会议", font=('Microsoft YaHei UI', 12, 'bold'),
            bg='#1890ff', fg='white', activebackground='#40a9ff',
            activeforeground='white', relief=tk.FLAT, cursor='hand2',
            command=self.toggle_meeting, width=12, height=2
        )
        self.start_meeting_btn.pack(side=tk.RIGHT, padx=10, pady=12)
        
        # 计时显示
        self.timer_label = tk.Label(control_frame, text="00:00:00", 
                                   font=('Consolas', 18, 'bold'),
                                   bg='white', fg='#1890ff')
        self.timer_label.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # 主内容区 - 三栏布局
        main_container = tk.Frame(frame, bg='#f0f2f5')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧 - 完整记录
        left_panel = tk.LabelFrame(main_container, text="📝 完整会议记录", 
                                  font=('Microsoft YaHei UI', 11, 'bold'),
                                  bg='white', fg='#333', padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.full_transcript = scrolledtext.ScrolledText(
            left_panel, font=('Microsoft YaHei UI', 11), wrap=tk.WORD,
            bg='#fafafa', relief=tk.FLAT, padx=10, pady=10
        )
        self.full_transcript.pack(fill=tk.BOTH, expand=True)
        
        # 中间 - 实时字幕
        center_panel = tk.LabelFrame(main_container, text="🎬 实时字幕", 
                                    font=('Microsoft YaHei UI', 11, 'bold'),
                                    bg='white', fg='#333', padx=10, pady=10)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.subtitle_display = SubtitleDisplay(center_panel, max_lines=5)
        
        # 右侧 - 智能分析
        right_panel = tk.LabelFrame(main_container, text="🤖 智能分析", 
                                   font=('Microsoft YaHei UI', 11, 'bold'),
                                   bg='white', fg='#333', padx=10, pady=10)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # 关键词区
        keyword_frame = tk.LabelFrame(right_panel, text="🔑 关键词", 
                                     font=('Microsoft YaHei UI', 10, 'bold'),
                                     bg='white', fg='#666')
        keyword_frame.pack(fill=tk.X, pady=5)
        
        self.keywords_container = tk.Frame(keyword_frame, bg='white')
        self.keywords_container.pack(fill=tk.X, padx=5, pady=5)
        self.keyword_labels = []
        
        # 行动项区
        action_frame = tk.LabelFrame(right_panel, text="✅ 行动项", 
                                    font=('Microsoft YaHei UI', 10, 'bold'),
                                    bg='white', fg='#666')
        action_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.action_items_text = scrolledtext.ScrolledText(
            action_frame, font=('Microsoft YaHei UI', 10), wrap=tk.WORD,
            bg='#fafafa', relief=tk.FLAT, padx=5, pady=5, height=10
        )
        self.action_items_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部操作栏
        bottom_frame = tk.Frame(frame, bg='white', height=60)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        bottom_frame.pack_propagate(False)
        
        tk.Button(bottom_frame, text="📊 生成总结", font=('Microsoft YaHei UI', 10),
                 bg='#52c41a', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.generate_summary, width=12, height=2
                 ).pack(side=tk.RIGHT, padx=10, pady=10)
        
        tk.Button(bottom_frame, text="💾 保存会议", font=('Microsoft YaHei UI', 10),
                 bg='#fa8c16', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.save_current_meeting, width=12, height=2
                 ).pack(side=tk.RIGHT, padx=10, pady=10)
        
        tk.Button(bottom_frame, text="🗑️ 清空内容", font=('Microsoft YaHei UI', 10),
                 bg='#ff4d4f', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.clear_meeting, width=12, height=2
                 ).pack(side=tk.RIGHT, padx=10, pady=10)
    
    def on_text_recognized(self, timestamp, raw_text, processed_text):
        """语音识别回调"""
        def update():
            self.full_transcript.insert(tk.END, f"[{timestamp}] ", 'time_tag')
            self.full_transcript.insert(tk.END, f"{processed_text}\n\n", 'content_tag')
            self.full_transcript.see(tk.END)
            
            full_text = self.full_transcript.get("1.0", tk.END)
            if len(full_text) > 200:
                self.update_analysis()
        
        self.root.after(0, update)
    
    def on_subtitle(self, text):
        """字幕回调"""
        def update():
            self.subtitle_display.add_line(text)
        
        self.root.after(0, update)
    
    def toggle_meeting(self):
        """开始/停止会议"""
        if not SPEECH_AVAILABLE:
            messagebox.showwarning(
                "功能不可用", 
                "语音识别功能未安装！\n\n请执行以下命令安装：\n"
                "pip install SpeechRecognition pyaudio\n\n"
                "macOS用户还需要安装：brew install portaudio"
            )
            return
        
        if not self.is_meeting_mode:
            try:
                self.meeting_recorder = MeetingRecorder(
                    self.on_text_recognized,
                    self.on_subtitle
                )
                self.meeting_recorder.start_recording()
                self.is_meeting_mode = True
                self.meeting_start_time = datetime.now()
                
                self.start_meeting_btn.config(text="⏹️ 结束会议", bg='#ff4d4f', activebackground='#ff7875')
                self.meeting_status.config(text="● 录音中", fg='#52c41a')
                
                self.subtitle_display.clear()
                self.start_timer()
                
                messagebox.showinfo("会议开始", "会议录音已开始，请开始讲话！\n\n系统将实时转写并智能分析。")
                
            except Exception as e:
                messagebox.showerror("错误", f"无法启动会议录音：\n{str(e)}\n\n请检查麦克风是否正常连接。")
                self.is_meeting_mode = False
        else:
            self.is_meeting_mode = False
            self.stop_timer()
            
            if self.meeting_recorder:
                self.meeting_recorder.stop_recording()
            
            self.start_meeting_btn.config(text="🎙️ 开始会议", bg='#1890ff', activebackground='#40a9ff')
            self.meeting_status.config(text="● 已结束", fg='#fa8c16')
            
            self.update_analysis()
            messagebox.showinfo("会议结束", "会议录音已结束！\n\n已生成完整记录和智能分析，请查看。")
    
    def start_timer(self):
        """启动计时器"""
        self.timer_running = True
        
        def update_timer():
            if self.timer_running and self.meeting_start_time:
                elapsed = datetime.now() - self.meeting_start_time
                hours = int(elapsed.total_seconds() // 3600)
                minutes = int((elapsed.total_seconds() % 3600) // 60)
                seconds = int(elapsed.total_seconds() % 60)
                self.timer_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                self.root.after(1000, update_timer)
        
        update_timer()
    
    def stop_timer(self):
        """停止计时器"""
        self.timer_running = False
    
    def update_analysis(self):
        """更新智能分析"""
        full_text = self.full_transcript.get("1.0", tk.END).strip()
        
        if not full_text:
            return
        
        keywords = MeetingSummarizer.extract_keywords(full_text, 12)
        actions = MeetingSummarizer.extract_action_items(full_text)
        
        for label in self.keyword_labels:
            label.destroy()
        self.keyword_labels = []
        
        if keywords:
            for keyword in keywords[:10]:
                label = tk.Label(
                    self.keywords_container, text=keyword,
                    font=('Microsoft YaHei UI', 9, 'bold'),
                    fg='#1890ff', bg='#e6f7ff',
                    padx=8, pady=3, cursor='hand2'
                )
                label.pack(side=tk.LEFT, padx=3, pady=3)
                self.keyword_labels.append(label)
        
        self.action_items_text.delete("1.0", tk.END)
        if actions:
            for i, action in enumerate(actions, 1):
                category = action.get('category', '')
                text = action.get('text', '')
                self.action_items_text.insert(tk.END, f"{i}. [{category}] {text}\n\n")
        else:
            self.action_items_text.insert(tk.END, "暂未识别到行动项")
    
    def generate_summary(self):
        """生成会议总结"""
        full_text = self.full_transcript.get("1.0", tk.END).strip()
        
        if not full_text:
            messagebox.showwarning("警告", "没有会议内容可以总结！")
            return
        
        summary = MeetingSummarizer.summarize(full_text)
        keywords = MeetingSummarizer.extract_keywords(full_text, 15)
        actions = MeetingSummarizer.extract_action_items(full_text)
        
        summary_window = tk.Toplevel(self.root)
        summary_window.title("📊 会议总结报告")
        summary_window.geometry("800x700")
        summary_window.configure(bg='#f0f2f5')
        
        canvas = tk.Canvas(summary_window, bg='#f0f2f5', highlightthickness=0)
        scrollbar = ttk.Scrollbar(summary_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f0f2f5')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        tk.Label(scrollable_frame, text="📊 会议总结报告", 
                font=('Microsoft YaHei UI', 20, 'bold'),
                bg='#f0f2f5', fg='#1890ff').pack(pady=15)
        
        # 基本信息
        info_frame = tk.LabelFrame(scrollable_frame, text="基本信息", 
                                  font=('Microsoft YaHei UI', 12, 'bold'),
                                  bg='white', fg='#333', padx=15, pady=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        theme = self.meeting_theme.get() or "未命名会议"
        attendees = self.meeting_attendees_input.get() or "未记录"
        
        tk.Label(info_frame, text=f"会议主题：{theme}", 
                font=('Microsoft YaHei UI', 11), bg='white', fg='#333').pack(anchor='w', pady=3)
        tk.Label(info_frame, text=f"参会人员：{attendees}", 
                font=('Microsoft YaHei UI', 11), bg='white', fg='#333').pack(anchor='w', pady=3)
        tk.Label(info_frame, text=f"会议时长：{self.timer_label.cget('text')}", 
                font=('Microsoft YaHei UI', 11), bg='white', fg='#333').pack(anchor='w', pady=3)
        tk.Label(info_frame, text=f"记录时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                font=('Microsoft YaHei UI', 11), bg='white', fg='#333').pack(anchor='w', pady=3)
        
        # 关键词
        keyword_frame = tk.LabelFrame(scrollable_frame, text="🔑 核心关键词", 
                                     font=('Microsoft YaHei UI', 12, 'bold'),
                                     bg='white', fg='#333', padx=15, pady=10)
        keyword_frame.pack(fill=tk.X, padx=20, pady=10)
        
        keyword_container = tk.Frame(keyword_frame, bg='white')
        keyword_container.pack(fill=tk.X, pady=5)
        
        for keyword in keywords[:12]:
            tk.Label(keyword_container, text=keyword,
                    font=('Microsoft YaHei UI', 10, 'bold'),
                    fg='#1890ff', bg='#e6f7ff',
                    padx=10, pady=5).pack(side=tk.LEFT, padx=5, pady=3)
        
        # 会议总结
        summary_frame = tk.LabelFrame(scrollable_frame, text="📝 会议总结", 
                                     font=('Microsoft YaHei UI', 12, 'bold'),
                                     bg='white', fg='#333', padx=15, pady=10)
        summary_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        summary_text = scrolledtext.ScrolledText(
            summary_frame, font=('Microsoft YaHei UI', 11),
            wrap=tk.WORD, height=10, bg='#fafafa', relief=tk.FLAT,
            padx=10, pady=10
        )
        summary_text.pack(fill=tk.BOTH, expand=True)
        summary_text.insert(tk.END, summary)
        summary_text.config(state=tk.DISABLED)
        
        # 行动项
        if actions:
            action_frame = tk.LabelFrame(scrollable_frame, text="✅ 行动项", 
                                        font=('Microsoft YaHei UI', 12, 'bold'),
                                        bg='white', fg='#333', padx=15, pady=10)
            action_frame.pack(fill=tk.X, padx=20, pady=10)
            
            for i, action in enumerate(actions, 1):
                category = action.get('category', '')
                text = action.get('text', '')
                tk.Label(action_frame, text=f"{i}. [{category}] {text}",
                        font=('Microsoft YaHei UI', 10), bg='white', fg='#333',
                        wraplength=650, justify='left').pack(anchor='w', pady=3)
    
    def save_current_meeting(self):
        """保存当前会议"""
        full_text = self.full_transcript.get("1.0", tk.END).strip()
        
        if not full_text:
            messagebox.showwarning("警告", "没有会议内容可以保存！")
            return
        
        theme = self.meeting_theme.get() or "未命名会议"
        attendees = self.meeting_attendees_input.get() or ""
        
        keywords = []
        for label in self.keyword_labels:
            keywords.append(label.cget('text'))
        
        actions = self.action_items_text.get("1.0", tk.END).strip()
        duration = self.timer_label.cget('text')
        
        summary = MeetingSummarizer.summarize(full_text)
        
        meeting = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": theme,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "attendees": attendees,
            "duration": duration,
            "full_text": full_text,
            "summary": summary,
            "keywords": ", ".join(keywords),
            "action_items": actions,
            "created_at": datetime.now().isoformat()
        }
        
        self.records["meetings"].insert(0, meeting)
        self.save_records()
        
        if hasattr(self, 'meeting_history_tree'):
            self.refresh_meeting_history()
        
        messagebox.showinfo("成功", f"会议已保存！\n\n主题：{theme}\n时长：{duration}")
    
    def clear_meeting(self):
        """清空会议内容"""
        if self.is_meeting_mode:
            if not messagebox.askyesno("确认", "会议正在进行中，确定要清空吗？"):
                return
            self.is_meeting_mode = False
            self.stop_timer()
            if self.meeting_recorder:
                self.meeting_recorder.stop_recording()
            self.start_meeting_btn.config(text="🎙️ 开始会议", bg='#1890ff', activebackground='#40a9ff')
            self.meeting_status.config(text="● 待机", fg='#999')
        
        if messagebox.askyesno("确认", "确定要清空所有会议内容吗？"):
            self.full_transcript.delete("1.0", tk.END)
            self.subtitle_display.clear()
            self.timer_label.config(text="00:00:00")
            self.meeting_theme.delete(0, tk.END)
            self.meeting_attendees_input.delete(0, tk.END)
            
            for label in self.keyword_labels:
                label.destroy()
            self.keyword_labels = []
            
            self.action_items_text.delete("1.0", tk.END)
    
    def create_meeting_history_tab(self):
        """创建会议历史标签页"""
        frame = tk.Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="📚 会议历史")
        
        list_frame = tk.LabelFrame(frame, text="历史会议记录", 
                                  font=('Microsoft YaHei UI', 12, 'bold'),
                                  bg='white', fg='#333', padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("time", "title", "attendees", "duration")
        self.meeting_history_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=15
        )
        self.meeting_history_tree.heading("time", text="时间")
        self.meeting_history_tree.heading("title", text="主题")
        self.meeting_history_tree.heading("attendees", text="参会人员")
        self.meeting_history_tree.heading("duration", text="时长")
        self.meeting_history_tree.column("time", width=160)
        self.meeting_history_tree.column("title", width=400)
        self.meeting_history_tree.column("attendees", width=200)
        self.meeting_history_tree.column("duration", width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                  command=self.meeting_history_tree.yview)
        self.meeting_history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.meeting_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.meeting_history_tree.bind("<<TreeviewSelect>>", self.show_meeting_history_detail)
        self.meeting_history_tree.bind("<Double-1>", self.delete_meeting_history)
        
        self.refresh_meeting_history()
    
    def refresh_meeting_history(self):
        """刷新会议历史列表"""
        for item in self.meeting_history_tree.get_children():
            self.meeting_history_tree.delete(item)
        
        for meeting in self.records["meetings"]:
            self.meeting_history_tree.insert("", tk.END, values=(
                meeting.get("time", ""),
                meeting.get("title", ""),
                meeting.get("attendees", ""),
                meeting.get("duration", "")
            ))
    
    def show_meeting_history_detail(self, event):
        """显示会议历史详情"""
        selection = self.meeting_history_tree.selection()
        if selection:
            index = self.meeting_history_tree.index(selection[0])
            if index < len(self.records["meetings"]):
                meeting = self.records["meetings"][index]
                self.show_meeting_detail_window(meeting)
    
    def show_meeting_detail_window(self, meeting):
        """显示会议详情窗口"""
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"会议详情 - {meeting.get('title', '')}")
        detail_window.geometry("1000x700")
        detail_window.configure(bg='#f0f2f5')
        
        notebook = ttk.Notebook(detail_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 完整记录标签
        full_frame = tk.Frame(notebook, bg='#f0f2f5')
        notebook.add(full_frame, text="📝 完整记录")
        
        full_text = scrolledtext.ScrolledText(
            full_frame, font=('Microsoft YaHei UI', 11), wrap=tk.WORD,
            bg='white', padx=10, pady=10
        )
        full_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        full_text.insert(tk.END, meeting.get("full_text", ""))
        full_text.config(state=tk.DISABLED)
        
        # 总结标签
        summary_frame = tk.Frame(notebook, bg='#f0f2f5')
        notebook.add(summary_frame, text="📊 智能总结")
        
        summary_container = tk.Frame(summary_frame, bg='#f0f2f5')
        summary_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 关键词
        kw_frame = tk.LabelFrame(summary_container, text="🔑 关键词", 
                                font=('Microsoft YaHei UI', 11, 'bold'),
                                bg='white', fg='#333')
        kw_frame.pack(fill=tk.X, pady=5)
        
        kw_text = meeting.get("keywords", "")
        if kw_text:
            kw_list = kw_text.split(", ")
            kw_box = tk.Frame(kw_frame, bg='white')
            kw_box.pack(fill=tk.X, padx=10, pady=10)
            for kw in kw_list:
                tk.Label(kw_box, text=kw.strip(),
                        font=('Microsoft YaHei UI', 10, 'bold'),
                        fg='#1890ff', bg='#e6f7ff',
                        padx=10, pady=5).pack(side=tk.LEFT, padx=5, pady=3)
        
        # 行动项
        act_frame = tk.LabelFrame(summary_container, text="✅ 行动项", 
                                 font=('Microsoft YaHei UI', 11, 'bold'),
                                 bg='white', fg='#333')
        act_frame.pack(fill=tk.X, pady=5)
        
        act_text_widget = scrolledtext.ScrolledText(
            act_frame, font=('Microsoft YaHei UI', 10), height=6,
            bg='#fafafa', padx=10, pady=10
        )
        act_text_widget.pack(fill=tk.X, padx=10, pady=10)
        act_text_widget.insert(tk.END, meeting.get("action_items", "暂无"))
        act_text_widget.config(state=tk.DISABLED)
        
        # 总结内容
        sum_frame = tk.LabelFrame(summary_container, text="📝 会议总结", 
                                 font=('Microsoft YaHei UI', 11, 'bold'),
                                 bg='white', fg='#333')
        sum_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        sum_text = scrolledtext.ScrolledText(
            sum_frame, font=('Microsoft YaHei UI', 11),
            bg='#fafafa', padx=10, pady=10
        )
        sum_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sum_text.insert(tk.END, meeting.get("summary", ""))
        sum_text.config(state=tk.DISABLED)
    
    def delete_meeting_history(self, event):
        """删除会议历史记录"""
        selection = self.meeting_history_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条会议记录吗？"):
                index = self.meeting_history_tree.index(selection[0])
                if index < len(self.records["meetings"]):
                    del self.records["meetings"][index]
                    self.save_records()
                    self.refresh_meeting_history()
    
    def create_work_tab(self):
        frame = tk.Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="📝 工作内容")
        
        input_frame = tk.LabelFrame(frame, text="新增工作记录", 
                                   font=('Microsoft YaHei UI', 12, 'bold'),
                                   bg='white', fg='#333', padx=10, pady=10)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="工作主题:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.work_title = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                  relief=tk.FLAT, bg='#f6f6f6')
        self.work_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        tk.Label(input_frame, text="工作日期:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.work_date = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                 relief=tk.FLAT, bg='#f6f6f6')
        self.work_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.work_date.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        tk.Label(input_frame, text="工作内容:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.work_content = scrolledtext.ScrolledText(input_frame, width=70, height=8,
                                                     font=('Microsoft YaHei UI', 10),
                                                     relief=tk.FLAT, bg='#f6f6f6')
        self.work_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        btn_frame = tk.Frame(input_frame, bg='white')
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="保存记录", font=('Microsoft YaHei UI', 10),
                 bg='#1890ff', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.save_work, width=15, height=2
                 ).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="清空内容", font=('Microsoft YaHei UI', 10),
                 bg='#ff4d4f', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.clear_work, width=15, height=2
                 ).pack(side=tk.LEFT, padx=5)
        
        list_frame = tk.LabelFrame(frame, text="历史工作记录", 
                                  font=('Microsoft YaHei UI', 12, 'bold'),
                                  bg='white', fg='#333', padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("date", "title", "preview")
        self.work_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.work_tree.heading("date", text="日期")
        self.work_tree.heading("title", text="主题")
        self.work_tree.heading("preview", text="内容预览")
        self.work_tree.column("date", width=120)
        self.work_tree.column("title", width=200)
        self.work_tree.column("preview", width=400)
        
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
                
                text = scrolledtext.ScrolledText(detail_window, width=70, height=20,
                                                 font=('Microsoft YaHei UI', 10))
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
        frame = tk.Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="🔍 工作细节")
        
        input_frame = tk.LabelFrame(frame, text="新增工作细节", 
                                   font=('Microsoft YaHei UI', 12, 'bold'),
                                   bg='white', fg='#333', padx=10, pady=10)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="细节主题:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.detail_title = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                    relief=tk.FLAT, bg='#f6f6f6')
        self.detail_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        tk.Label(input_frame, text="记录时间:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.detail_time = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                   relief=tk.FLAT, bg='#f6f6f6')
        self.detail_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.detail_time.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        tk.Label(input_frame, text="详细内容:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.detail_content = scrolledtext.ScrolledText(input_frame, width=70, height=8,
                                                       font=('Microsoft YaHei UI', 10),
                                                       relief=tk.FLAT, bg='#f6f6f6')
        self.detail_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        btn_frame = tk.Frame(input_frame, bg='white')
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="保存记录", font=('Microsoft YaHei UI', 10),
                 bg='#1890ff', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.save_detail, width=15, height=2
                 ).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="清空内容", font=('Microsoft YaHei UI', 10),
                 bg='#ff4d4f', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.clear_detail, width=15, height=2
                 ).pack(side=tk.LEFT, padx=5)
        
        list_frame = tk.LabelFrame(frame, text="历史细节记录", 
                                  font=('Microsoft YaHei UI', 12, 'bold'),
                                  bg='white', fg='#333', padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("time", "title", "preview")
        self.detail_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.detail_tree.heading("time", text="时间")
        self.detail_tree.heading("title", text="主题")
        self.detail_tree.heading("preview", text="内容预览")
        self.detail_tree.column("time", width=150)
        self.detail_tree.column("title", width=200)
        self.detail_tree.column("preview", width=370)
        
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
                
                text = scrolledtext.ScrolledText(detail_window, width=70, height=20,
                                                 font=('Microsoft YaHei UI', 10))
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
        frame = tk.Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="💡 改进建议")
        
        input_frame = tk.LabelFrame(frame, text="新增改进建议", 
                                   font=('Microsoft YaHei UI', 12, 'bold'),
                                   bg='white', fg='#333', padx=10, pady=10)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="改进主题:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_title = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                         relief=tk.FLAT, bg='#f6f6f6')
        self.improvement_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        tk.Label(input_frame, text="提出日期:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_date = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                        relief=tk.FLAT, bg='#f6f6f6')
        self.improvement_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.improvement_date.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        tk.Label(input_frame, text="改进内容:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.improvement_content = scrolledtext.ScrolledText(input_frame, width=70, height=8,
                                                           font=('Microsoft YaHei UI', 10),
                                                           relief=tk.FLAT, bg='#f6f6f6')
        self.improvement_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        tk.Label(input_frame, text="状态:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_status = ttk.Combobox(input_frame, values=["待处理", "进行中", "已完成"], width=57)
        self.improvement_status.set("待处理")
        self.improvement_status.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        btn_frame = tk.Frame(input_frame, bg='white')
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="保存记录", font=('Microsoft YaHei UI', 10),
                 bg='#1890ff', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.save_improvement, width=15, height=2
                 ).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="清空内容", font=('Microsoft YaHei UI', 10),
                 bg='#ff4d4f', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.clear_improvement, width=15, height=2
                 ).pack(side=tk.LEFT, padx=5)
        
        list_frame = tk.LabelFrame(frame, text="历史改进记录", 
                                  font=('Microsoft YaHei UI', 12, 'bold'),
                                  bg='white', fg='#333', padx=10, pady=10)
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
        self.improvement_tree.column("preview", width=370)
        
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
                
                text = scrolledtext.ScrolledText(detail_window, width=70, height=20,
                                                 font=('Microsoft YaHei UI', 10))
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
        frame = tk.Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="⏰ 会议提醒")
        
        input_frame = tk.LabelFrame(frame, text="新增会议提醒", 
                                   font=('Microsoft YaHei UI', 12, 'bold'),
                                   bg='white', fg='#333', padx=10, pady=10)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="会议主题:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_title = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                      relief=tk.FLAT, bg='#f6f6f6')
        self.reminder_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        tk.Label(input_frame, text="会议时间:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_time = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                     relief=tk.FLAT, bg='#f6f6f6')
        self.reminder_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.reminder_time.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        tk.Label(input_frame, text="提前提醒:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_advance = ttk.Combobox(input_frame, values=["5分钟", "10分钟", "15分钟", "30分钟", "1小时"], width=57)
        self.reminder_advance.set("15分钟")
        self.reminder_advance.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        tk.Label(input_frame, text="备注:", font=('Microsoft YaHei UI', 10), 
                bg='white', fg='#333').grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_note = tk.Entry(input_frame, width=60, font=('Microsoft YaHei UI', 10),
                                     relief=tk.FLAT, bg='#f6f6f6')
        self.reminder_note.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W, ipady=5)
        
        btn_frame = tk.Frame(input_frame, bg='white')
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="添加提醒", font=('Microsoft YaHei UI', 10),
                 bg='#1890ff', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.add_reminder, width=15, height=2
                 ).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="清空内容", font=('Microsoft YaHei UI', 10),
                 bg='#ff4d4f', fg='white', relief=tk.FLAT, cursor='hand2',
                 command=self.clear_reminder, width=15, height=2
                 ).pack(side=tk.LEFT, padx=5)
        
        list_frame = tk.LabelFrame(frame, text="已设置的提醒", 
                                  font=('Microsoft YaHei UI', 12, 'bold'),
                                  bg='white', fg='#333', padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("time", "title", "advance", "note")
        self.reminder_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.reminder_tree.heading("time", text="会议时间")
        self.reminder_tree.heading("title", text="主题")
        self.reminder_tree.heading("advance", text="提前提醒")
        self.reminder_tree.heading("note", text="备注")
        self.reminder_tree.column("time", width=160)
        self.reminder_tree.column("title", width=250)
        self.reminder_tree.column("advance", width=100)
        self.reminder_tree.column("note", width=250)
        
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
                                pass
                    
                    time.sleep(30)
                except Exception as e:
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
    
    def on_closing(self):
        if self.is_meeting_mode and self.meeting_recorder:
            self.meeting_recorder.stop_recording()
        self.reminder_running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = WorkAssistant(root)
    root.mainloop()


if __name__ == "__main__":
    main()