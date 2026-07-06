# -*- coding: utf-8 -*-
"""
工作助手 - 安卓版本
专业会议记录应用
"""

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex

from datetime import datetime, timedelta
import json
import os
import threading
import time
import re

try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False

kivy.require('2.0.0')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
RECORDS_FILE = os.path.join(DATA_DIR, 'records.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')


class TextProcessor:
    @staticmethod
    def auto_punctuate(text):
        if not text.strip():
            return text
        text = text.strip()
        
        patterns = [
            (r'(今天|明天|昨天|后天|前天|上周|下周|本月|下月|今年|明年)\s*', r'\1，'),
            (r'(首先|其次|然后|接着|最后|另外|此外|同时|因此|所以)', r'\1，'),
            (r'(好的|好的好的|明白了|了解了|知道了|收到|对的|是的|没错)', r'\1。'),
            (r'(谢谢|感谢|非常感谢|辛苦|辛苦了)', r'\1。'),
            (r'(那么|既然这样|这样的话|所以说|也就是说)', r'\1，'),
            (r'(等等|之类的|什么的)', r'\1。'),
            (r'(吧|呢|啊|吗|嘛|啦|呀|哦)$', r'\1？'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        
        if text and text[-1] not in '。！？，、；：':
            text += '。'
        
        text = re.sub(r'[，。！？、；：]{2,}', lambda m: m.group(0)[-1], text)
        return text
    
    @staticmethod
    def correct_common_errors(text):
        corrections = {
            '的话的': '的话', '然后然后': '然后', '就是就是': '就是',
            '这个这个': '这个', '那个那个': '那个', '因为因为': '因为',
            '所以所以': '所以', '但是但是': '但是', '的的': '的',
            '了了': '了', '着着': '着', '在在': '在', '是是': '是',
            '有有': '有', '我我': '我', '你你': '你', '他他': '他',
            '我们我们': '我们', '你们你们': '你们', '他们他们': '他们',
            '大家大家': '大家', '问题问题': '问题', '事情事情': '事情',
            '东西东西': '东西', '时间时间': '时间', '现在现在': '现在',
            '今天今天': '今天', '明天明天': '明天', '工作工作': '工作',
            '项目项目': '项目', '任务任务': '任务', '计划计划': '计划',
            '进度进度': '进度', '报告报告': '报告', '会议会议': '会议',
            '讨论讨论': '讨论', '沟通沟通': '沟通', '协调协调': '协调',
            '安排安排': '安排', '落实落实': '落实', '执行执行': '执行',
            '完成完成': '完成', '准备准备': '准备', '开始开始': '开始',
            '结束结束': '结束', '进行进行': '进行',
        }
        
        for wrong, right in corrections.items():
            text = text.replace(wrong, right)
        return text
    
    @staticmethod
    def process_text(text):
        if not text.strip():
            return text
        text = TextProcessor.correct_common_errors(text)
        text = TextProcessor.auto_punctuate(text)
        text = TextProcessor.correct_common_errors(text)
        return text


class MeetingRecorder:
    def __init__(self, callback):
        self.callback = callback
        self.is_recording = False
        self.recognizer = None
        self.microphone = None
        self.recording_thread = None
        self.full_text = []
    
    def start_recording(self):
        if not SPEECH_AVAILABLE:
            raise Exception("语音识别不可用")
        
        self.is_recording = True
        self.full_text = []
        
        def record_loop():
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 300
                self.recognizer.pause_threshold = 0.8
                
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    
                    while self.is_recording:
                        try:
                            audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                            text = self.recognizer.recognize_google(audio, language='zh-CN')
                            
                            if text and len(text.strip()) > 0:
                                processed = TextProcessor.process_text(text.strip())
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                self.full_text.append({'time': timestamp, 'text': processed})
                                
                                if self.callback:
                                    self.callback(timestamp, processed)
                            
                        except sr.WaitTimeoutError:
                            continue
                        except sr.UnknownValueError:
                            continue
                        except Exception as e:
                            time.sleep(1)
            except Exception as e:
                pass
        
        self.recording_thread = threading.Thread(target=record_loop, daemon=True)
        self.recording_thread.start()
    
    def stop_recording(self):
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=3)
        return self.full_text


class MeetingSummarizer:
    @staticmethod
    def extract_keywords(text, num_keywords=10):
        if not text.strip():
            return []
        
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
    def summarize(text, max_sentences=5):
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
            score += 1 / (1 + i)
            scores.append((i, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        selected_indices = sorted([i for i, score in scores[:max_sentences]])
        
        return ''.join([result[i] for i in selected_indices])
    
    @staticmethod
    def extract_action_items(text):
        patterns = [
            (r'(需要|必须|应该|得|务必)\s*(做|完成|处理|解决|提交|跟进|落实)\s*([^。！？\n]+)', '需要'),
            (r'(负责|承担)\s*([^。！？\n]+)', '负责'),
            (r'(截止|限期)\s*([^。！？\n]+)', '时间'),
            (r'(下一步|接下来)\s*(做|进行)\s*([^。！？\n]+)', '下一步'),
        ]
        
        action_items = []
        for pattern, category in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                item = ''.join(str(m) for m in match).strip()
                if item and len(item) > 3:
                    action_items.append({'text': item, 'category': category})
        
        return action_items[:10]


class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = get_color_from_hex('#1890ff')
        self.color = (1, 1, 1, 1)
        self.font_size = 16
        self.padding = [10, 5]


class StyledLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = get_color_from_hex('#333333')
        self.font_size = 14


class StyledTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0.96, 0.96, 0.96, 1)
        self.font_size = 14
        self.padding = [10, 5]


class MeetingTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.padding = [10, 10, 10, 10]
        self.spacing = 10
        
        self.meeting_recorder = None
        self.is_recording = False
        self.meeting_start_time = None
        self.timer_running = False
        self.timer_label = None
        
        self.build_ui()
    
    def build_ui(self):
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        
        self.theme_input = StyledTextInput(hint_text='会议主题', size_hint_x=0.4)
        top_bar.add_widget(self.theme_input)
        
        self.attendees_input = StyledTextInput(hint_text='参会人员', size_hint_x=0.3)
        top_bar.add_widget(self.attendees_input)
        
        self.record_btn = StyledButton(text='开始录音', size_hint_x=0.3, on_press=self.toggle_recording)
        top_bar.add_widget(self.record_btn)
        
        self.add_widget(top_bar)
        
        timer_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        self.timer_label = Label(text='00:00:00', font_size=20, color=get_color_from_hex('#1890ff'), bold=True)
        timer_bar.add_widget(self.timer_label)
        
        self.status_label = Label(text='待机', color=get_color_from_hex('#999999'))
        timer_bar.add_widget(self.status_label)
        
        self.add_widget(timer_bar)
        
        content_area = BoxLayout(orientation='horizontal', spacing=10)
        
        left_panel = BoxLayout(orientation='vertical', size_hint_x=0.4)
        left_panel.add_widget(Label(text='完整记录', font_size=16, bold=True, size_hint_y=None, height=30))
        
        self.full_transcript = TextInput(
            readonly=True,
            text='',
            font_size=14,
            padding=[10, 10],
            background_color=(0.98, 0.98, 0.98, 1),
            scroll_type=['bars', 'content'],
            bar_width=10,
        )
        left_panel.add_widget(self.full_transcript)
        content_area.add_widget(left_panel)
        
        right_panel = BoxLayout(orientation='vertical', size_hint_x=0.6)
        
        subtitle_box = BoxLayout(orientation='vertical', size_hint_y=0.4)
        subtitle_box.add_widget(Label(text='实时字幕', font_size=16, bold=True, size_hint_y=None, height=30))
        
        self.subtitle_text = TextInput(
            readonly=True,
            text='',
            font_size=16,
            padding=[10, 10],
            background_color=get_color_from_hex('#1a1a2e'),
            foreground_color=(1, 1, 1, 1),
        )
        subtitle_box.add_widget(self.subtitle_text)
        right_panel.add_widget(subtitle_box)
        
        analysis_box = BoxLayout(orientation='vertical', size_hint_y=0.6)
        analysis_box.add_widget(Label(text='智能分析', font_size=16, bold=True, size_hint_y=None, height=30))
        
        self.keywords_label = Label(text='关键词:', font_size=14, size_hint_y=None, height=30)
        analysis_box.add_widget(self.keywords_label)
        
        self.action_items_text = TextInput(
            readonly=True,
            text='行动项:',
            font_size=14,
            padding=[10, 10],
            background_color=(0.98, 0.98, 0.98, 1),
        )
        analysis_box.add_widget(self.action_items_text)
        
        right_panel.add_widget(analysis_box)
        content_area.add_widget(right_panel)
        
        self.add_widget(content_area)
        
        bottom_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        
        self.generate_btn = StyledButton(text='生成总结', on_press=self.generate_summary, background_color=get_color_from_hex('#52c41a'))
        bottom_bar.add_widget(self.generate_btn)
        
        self.save_btn = StyledButton(text='保存会议', on_press=self.save_meeting, background_color=get_color_from_hex('#fa8c16'))
        bottom_bar.add_widget(self.save_btn)
        
        self.clear_btn = StyledButton(text='清空', on_press=self.clear_meeting, background_color=get_color_from_hex('#ff4d4f'))
        bottom_bar.add_widget(self.clear_btn)
        
        self.add_widget(bottom_bar)
    
    def on_text_recognized(self, timestamp, text):
        self.full_transcript.text += f"[{timestamp}] {text}\n\n"
        self.subtitle_text.text = text
        
        full_text = self.full_transcript.text
        if len(full_text) > 200:
            self.update_analysis()
    
    def toggle_recording(self, instance):
        if not self.is_recording:
            try:
                self.meeting_recorder = MeetingRecorder(self.on_text_recognized)
                self.meeting_recorder.start_recording()
                self.is_recording = True
                self.meeting_start_time = datetime.now()
                
                self.record_btn.text = '停止录音'
                self.record_btn.background_color = get_color_from_hex('#ff4d4f')
                self.status_label.text = '录音中...'
                self.status_label.color = get_color_from_hex('#52c41a')
                
                self.start_timer()
                
            except Exception as e:
                self.show_popup('错误', f'无法启动录音:\n{str(e)}')
                self.is_recording = False
        else:
            self.is_recording = False
            self.stop_timer()
            
            if self.meeting_recorder:
                self.meeting_recorder.stop_recording()
            
            self.record_btn.text = '开始录音'
            self.record_btn.background_color = get_color_from_hex('#1890ff')
            self.status_label.text = '已结束'
            self.status_label.color = get_color_from_hex('#fa8c16')
            
            self.update_analysis()
            self.show_popup('完成', '会议录音已结束！')
    
    def start_timer(self):
        self.timer_running = True
        
        def update_timer(dt):
            if self.timer_running and self.meeting_start_time:
                elapsed = datetime.now() - self.meeting_start_time
                hours = int(elapsed.total_seconds() // 3600)
                minutes = int((elapsed.total_seconds() % 3600) // 60)
                seconds = int(elapsed.total_seconds() % 60)
                self.timer_label.text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        Clock.schedule_interval(update_timer, 1)
    
    def stop_timer(self):
        self.timer_running = False
        Clock.unschedule(self.start_timer)
    
    def update_analysis(self):
        full_text = self.full_transcript.text.strip()
        if not full_text:
            return
        
        keywords = MeetingSummarizer.extract_keywords(full_text, 8)
        actions = MeetingSummarizer.extract_action_items(full_text)
        
        self.keywords_label.text = f"关键词: {' '.join(keywords)}"
        
        action_text = "行动项:\n"
        for i, action in enumerate(actions, 1):
            action_text += f"{i}. [{action['category']}] {action['text']}\n"
        
        self.action_items_text.text = action_text if actions else "行动项: 暂未识别到"
    
    def generate_summary(self, instance):
        full_text = self.full_transcript.text.strip()
        if not full_text:
            self.show_popup('警告', '没有内容可以总结！')
            return
        
        summary = MeetingSummarizer.summarize(full_text)
        keywords = MeetingSummarizer.extract_keywords(full_text, 10)
        
        content = f"会议总结:\n{summary}\n\n关键词:\n{' '.join(keywords)}"
        self.show_popup('会议总结', content)
    
    def save_meeting(self, instance):
        full_text = self.full_transcript.text.strip()
        if not full_text:
            self.show_popup('警告', '没有内容可以保存！')
            return
        
        theme = self.theme_input.text or '未命名会议'
        attendees = self.attendees_input.text or ''
        duration = self.timer_label.text
        
        meeting = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": theme,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "attendees": attendees,
            "duration": duration,
            "full_text": full_text,
            "created_at": datetime.now().isoformat()
        }
        
        records = self.app.load_records()
        records["meetings"].insert(0, meeting)
        self.app.save_records(records)
        
        self.show_popup('成功', f'会议已保存！\n主题: {theme}\n时长: {duration}')
    
    def clear_meeting(self, instance):
        self.full_transcript.text = ''
        self.subtitle_text.text = ''
        self.timer_label.text = '00:00:00'
        self.theme_input.text = ''
        self.attendees_input.text = ''
        self.keywords_label.text = '关键词:'
        self.action_items_text.text = '行动项:'
        self.status_label.text = '待机'
        self.status_label.color = get_color_from_hex('#999999')
    
    def show_popup(self, title, content):
        popup = Popup(
            title=title,
            content=Label(text=content, text_size=(400, None), padding=[20, 20]),
            size_hint=(0.8, 0.6),
            auto_dismiss=True
        )
        popup.open()


class HistoryTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.padding = [10, 10, 10, 10]
        self.spacing = 10
        
        self.build_ui()
    
    def build_ui(self):
        self.add_widget(Label(text='会议历史', font_size=20, bold=True, size_hint_y=None, height=40))
        
        self.history_list = ScrollView()
        self.history_content = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.history_content.bind(minimum_height=self.history_content.setter('height'))
        
        self.load_history()
        
        self.history_list.add_widget(self.history_content)
        self.add_widget(self.history_list)
    
    def load_history(self):
        self.history_content.clear_widgets()
        records = self.app.load_records()
        
        for meeting in records.get("meetings", []):
            item = BoxLayout(orientation='vertical', padding=[10, 10], background_color=(0.95, 0.95, 0.95, 1))
            item.add_widget(Label(text=meeting.get('title', ''), font_size=16, bold=True))
            item.add_widget(Label(text=f"时间: {meeting.get('time', '')} 时长: {meeting.get('duration', '')}"))
            item.add_widget(Label(text=f"参会: {meeting.get('attendees', '')}"))
            
            view_btn = Button(text='查看详情', size_hint_y=None, height=40, on_press=lambda btn, m=meeting: self.view_detail(m))
            item.add_widget(view_btn)
            
            self.history_content.add_widget(item)
    
    def view_detail(self, meeting):
        content = f"主题: {meeting.get('title', '')}\n\n"
        content += f"时间: {meeting.get('time', '')}\n"
        content += f"时长: {meeting.get('duration', '')}\n"
        content += f"参会: {meeting.get('attendees', '')}\n\n"
        content += f"内容:\n{meeting.get('full_text', '')[:500]}..."
        
        popup = Popup(
            title='会议详情',
            content=Label(text=content, text_size=(500, None), padding=[20, 20]),
            size_hint=(0.9, 0.8),
            auto_dismiss=True
        )
        popup.open()


class WorkTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.padding = [10, 10, 10, 10]
        self.spacing = 10
        
        self.build_ui()
    
    def build_ui(self):
        self.add_widget(Label(text='工作内容', font_size=20, bold=True, size_hint_y=None, height=40))
        
        self.title_input = StyledTextInput(hint_text='工作主题', size_hint_y=None, height=50)
        self.add_widget(self.title_input)
        
        self.date_input = StyledTextInput(hint_text='工作日期', size_hint_y=None, height=50)
        self.date_input.text = datetime.now().strftime("%Y-%m-%d")
        self.add_widget(self.date_input)
        
        self.content_input = TextInput(
            hint_text='工作内容',
            font_size=14,
            padding=[10, 10],
            size_hint_y=0.5,
        )
        self.add_widget(self.content_input)
        
        btn_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        btn_bar.add_widget(StyledButton(text='保存', on_press=self.save_work))
        btn_bar.add_widget(StyledButton(text='清空', on_press=self.clear_work, background_color=get_color_from_hex('#ff4d4f')))
        self.add_widget(btn_bar)
    
    def save_work(self, instance):
        title = self.title_input.text.strip()
        date = self.date_input.text.strip()
        content = self.content_input.text.strip()
        
        if not title or not content:
            self.show_popup('警告', '请填写主题和内容！')
            return
        
        work = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "date": date,
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        
        records = self.app.load_records()
        records["works"].insert(0, work)
        self.app.save_records(records)
        
        self.show_popup('成功', '工作记录已保存！')
        self.clear_work(instance)
    
    def clear_work(self, instance):
        self.title_input.text = ''
        self.date_input.text = datetime.now().strftime("%Y-%m-%d")
        self.content_input.text = ''
    
    def show_popup(self, title, content):
        popup = Popup(
            title=title,
            content=Label(text=content, padding=[20, 20]),
            size_hint=(0.8, 0.6),
            auto_dismiss=True
        )
        popup.open()


class ImprovementTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.padding = [10, 10, 10, 10]
        self.spacing = 10
        
        self.build_ui()
    
    def build_ui(self):
        self.add_widget(Label(text='改进建议', font_size=20, bold=True, size_hint_y=None, height=40))
        
        self.title_input = StyledTextInput(hint_text='改进主题', size_hint_y=None, height=50)
        self.add_widget(self.title_input)
        
        self.date_input = StyledTextInput(hint_text='日期', size_hint_y=None, height=50)
        self.date_input.text = datetime.now().strftime("%Y-%m-%d")
        self.add_widget(self.date_input)
        
        self.content_input = TextInput(
            hint_text='改进内容',
            font_size=14,
            padding=[10, 10],
            size_hint_y=0.5,
        )
        self.add_widget(self.content_input)
        
        btn_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        btn_bar.add_widget(StyledButton(text='保存', on_press=self.save_improvement))
        btn_bar.add_widget(StyledButton(text='清空', on_press=self.clear_improvement, background_color=get_color_from_hex('#ff4d4f')))
        self.add_widget(btn_bar)
    
    def save_improvement(self, instance):
        title = self.title_input.text.strip()
        date = self.date_input.text.strip()
        content = self.content_input.text.strip()
        
        if not title or not content:
            self.show_popup('警告', '请填写主题和内容！')
            return
        
        improvement = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "date": date,
            "content": content,
            "status": "待处理",
            "created_at": datetime.now().isoformat()
        }
        
        records = self.app.load_records()
        records["improvements"].insert(0, improvement)
        self.app.save_records(records)
        
        self.show_popup('成功', '改进建议已保存！')
        self.clear_improvement(instance)
    
    def clear_improvement(self, instance):
        self.title_input.text = ''
        self.date_input.text = datetime.now().strftime("%Y-%m-%d")
        self.content_input.text = ''
    
    def show_popup(self, title, content):
        popup = Popup(
            title=title,
            content=Label(text=content, padding=[20, 20]),
            size_hint=(0.8, 0.6),
            auto_dismiss=True
        )
        popup.open()


class WorkAssistantApp(App):
    def build(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        
        self.title = '工作助手'
        self.icon = None
        
        main_layout = TabbedPanel(do_default_tab=False)
        
        meeting_tab = TabbedPanelItem(text='🎙️ 会议')
        meeting_tab.add_widget(MeetingTab(self))
        main_layout.add_widget(meeting_tab)
        
        history_tab = TabbedPanelItem(text='📚 历史')
        history_tab.add_widget(HistoryTab(self))
        main_layout.add_widget(history_tab)
        
        work_tab = TabbedPanelItem(text='📝 工作')
        work_tab.add_widget(WorkTab(self))
        main_layout.add_widget(work_tab)
        
        improvement_tab = TabbedPanelItem(text='💡 改进')
        improvement_tab.add_widget(ImprovementTab(self))
        main_layout.add_widget(improvement_tab)
        
        return main_layout
    
    def load_records(self):
        if os.path.exists(RECORDS_FILE):
            try:
                with open(RECORDS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"meetings": [], "works": [], "details": [], "improvements": []}
    
    def save_records(self, records):
        with open(RECORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    WorkAssistantApp().run()