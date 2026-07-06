#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作助手应用 - 自动记录会议要点、工作内容和改进建议
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
import json
import os
import threading
import time
from pathlib import Path

# 数据存储路径
DATA_DIR = Path(__file__).parent / "data"
RECORDS_FILE = DATA_DIR / "records.json"
CONFIG_FILE = DATA_DIR / "config.json"


class WorkAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("工作助手 - 会议与工作记录")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # 确保数据目录存在
        DATA_DIR.mkdir(exist_ok=True)
        
        # 加载数据
        self.records = self.load_records()
        self.config = self.load_config()
        
        # 会议提醒线程控制
        self.reminder_running = True
        self.reminder_thread = None
        
        # 创建界面
        self.create_widgets()
        
        # 启动会议提醒
        self.start_reminder_service()
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_records(self):
        """加载记录数据"""
        if RECORDS_FILE.exists():
            try:
                with open(RECORDS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.get_default_records()
        return self.get_default_records()
    
    def get_default_records(self):
        """获取默认记录结构"""
        return {
            "meetings": [],
            "works": [],
            "details": [],
            "improvements": []
        }
    
    def load_config(self):
        """加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"reminders": []}
        return {"reminders": []}
    
    def save_records(self):
        """保存记录数据"""
        with open(RECORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
    
    def save_config(self):
        """保存配置"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 会议要点标签页
        self.create_meeting_tab()
        
        # 工作内容标签页
        self.create_work_tab()
        
        # 工作细节标签页
        self.create_detail_tab()
        
        # 改进建议标签页
        self.create_improvement_tab()
        
        # 会议提醒标签页
        self.create_reminder_tab()
        
        # 底部状态栏
        self.create_status_bar()
    
    def create_meeting_tab(self):
        """创建会议要点标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📋 会议要点")
        
        # 输入区域
        input_frame = ttk.LabelFrame(frame, text="新增会议记录")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 会议主题
        ttk.Label(input_frame, text="会议主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.meeting_title = ttk.Entry(input_frame, width=50)
        self.meeting_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 会议时间
        ttk.Label(input_frame, text="会议时间:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.meeting_time = ttk.Entry(input_frame, width=50)
        self.meeting_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.meeting_time.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 参会人员
        ttk.Label(input_frame, text="参会人员:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.meeting_attendees = ttk.Entry(input_frame, width=50)
        self.meeting_attendees.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 会议要点
        ttk.Label(input_frame, text="会议要点:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.NW)
        self.meeting_content = scrolledtext.ScrolledText(input_frame, width=60, height=8)
        self.meeting_content.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 按钮
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="保存记录", command=self.save_meeting).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_meeting).pack(side=tk.LEFT, padx=5)
        
        # 记录列表
        list_frame = ttk.LabelFrame(frame, text="历史会议记录")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建树形视图
        columns = ("time", "title", "attendees")
        self.meeting_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.meeting_tree.heading("time", text="时间")
        self.meeting_tree.heading("title", text="主题")
        self.meeting_tree.heading("attendees", text="参会人员")
        self.meeting_tree.column("time", width=150)
        self.meeting_tree.column("title", width=300)
        self.meeting_tree.column("attendees", width=200)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.meeting_tree.yview)
        self.meeting_tree.configure(yscrollcommand=scrollbar.set)
        
        self.meeting_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.meeting_tree.bind("<<TreeviewSelect>>", self.show_meeting_detail)
        self.meeting_tree.bind("<Double-1>", self.delete_meeting)
        
        # 加载历史记录
        self.refresh_meeting_list()
    
    def create_work_tab(self):
        """创建工作内容标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📝 工作内容")
        
        # 输入区域
        input_frame = ttk.LabelFrame(frame, text="新增工作记录")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 工作主题
        ttk.Label(input_frame, text="工作主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.work_title = ttk.Entry(input_frame, width=50)
        self.work_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 工作日期
        ttk.Label(input_frame, text="工作日期:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.work_date = ttk.Entry(input_frame, width=50)
        self.work_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.work_date.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 工作内容
        ttk.Label(input_frame, text="工作内容:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.work_content = scrolledtext.ScrolledText(input_frame, width=60, height=8)
        self.work_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 按钮
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="保存记录", command=self.save_work).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_work).pack(side=tk.LEFT, padx=5)
        
        # 记录列表
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
    
    def create_detail_tab(self):
        """创建工作细节标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔍 工作细节")
        
        # 输入区域
        input_frame = ttk.LabelFrame(frame, text="新增工作细节")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 细节主题
        ttk.Label(input_frame, text="细节主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.detail_title = ttk.Entry(input_frame, width=50)
        self.detail_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 记录时间
        ttk.Label(input_frame, text="记录时间:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.detail_time = ttk.Entry(input_frame, width=50)
        self.detail_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.detail_time.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 详细内容
        ttk.Label(input_frame, text="详细内容:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.detail_content = scrolledtext.ScrolledText(input_frame, width=60, height=8)
        self.detail_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 按钮
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="保存记录", command=self.save_detail).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_detail).pack(side=tk.LEFT, padx=5)
        
        # 记录列表
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
    
    def create_improvement_tab(self):
        """创建改进建议标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💡 改进建议")
        
        # 输入区域
        input_frame = ttk.LabelFrame(frame, text="新增改进建议")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 改进主题
        ttk.Label(input_frame, text="改进主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_title = ttk.Entry(input_frame, width=50)
        self.improvement_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 提出日期
        ttk.Label(input_frame, text="提出日期:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_date = ttk.Entry(input_frame, width=50)
        self.improvement_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.improvement_date.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 改进内容
        ttk.Label(input_frame, text="改进内容:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.NW)
        self.improvement_content = scrolledtext.ScrolledText(input_frame, width=60, height=8)
        self.improvement_content.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 改进状态
        ttk.Label(input_frame, text="状态:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.improvement_status = ttk.Combobox(input_frame, values=["待处理", "进行中", "已完成"], width=47)
        self.improvement_status.set("待处理")
        self.improvement_status.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 按钮
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="保存记录", command=self.save_improvement).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_improvement).pack(side=tk.LEFT, padx=5)
        
        # 记录列表
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
    
    def create_reminder_tab(self):
        """创建会议提醒标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⏰ 会议提醒")
        
        # 输入区域
        input_frame = ttk.LabelFrame(frame, text="新增会议提醒")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 提醒主题
        ttk.Label(input_frame, text="会议主题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_title = ttk.Entry(input_frame, width=50)
        self.reminder_title.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 会议时间
        ttk.Label(input_frame, text="会议时间:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_time = ttk.Entry(input_frame, width=50)
        self.reminder_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.reminder_time.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 提前提醒
        ttk.Label(input_frame, text="提前提醒:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_advance = ttk.Combobox(input_frame, values=["5分钟", "10分钟", "15分钟", "30分钟", "1小时"], width=47)
        self.reminder_advance.set("15分钟")
        self.reminder_advance.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 备注
        ttk.Label(input_frame, text="备注:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.reminder_note = ttk.Entry(input_frame, width=50)
        self.reminder_note.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 按钮
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="添加提醒", command=self.add_reminder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空内容", command=self.clear_reminder).pack(side=tk.LEFT, padx=5)
        
        # 提醒列表
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
    
    def create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)
        
        ttk.Label(status_frame, text=f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}").pack(side=tk.RIGHT)
    
    # 会议相关方法
    def save_meeting(self):
        """保存会议记录"""
        title = self.meeting_title.get().strip()
        time = self.meeting_time.get().strip()
        attendees = self.meeting_attendees.get().strip()
        content = self.meeting_content.get("1.0", tk.END).strip()
        
        if not title or not content:
            messagebox.showwarning("警告", "请填写会议主题和会议要点！")
            return
        
        meeting = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "time": time,
            "attendees": attendees,
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        
        self.records["meetings"].insert(0, meeting)
        self.save_records()
        self.refresh_meeting_list()
        self.clear_meeting()
        messagebox.showinfo("成功", "会议记录已保存！")
    
    def clear_meeting(self):
        """清空会议输入"""
        self.meeting_title.delete(0, tk.END)
        self.meeting_time.delete(0, tk.END)
        self.meeting_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.meeting_attendees.delete(0, tk.END)
        self.meeting_content.delete("1.0", tk.END)
    
    def refresh_meeting_list(self):
        """刷新会议列表"""
        for item in self.meeting_tree.get_children():
            self.meeting_tree.delete(item)
        
        for meeting in self.records["meetings"]:
            self.meeting_tree.insert("", tk.END, values=(
                meeting.get("time", ""),
                meeting.get("title", ""),
                meeting.get("attendees", "")
            ))
    
    def show_meeting_detail(self, event):
        """显示会议详情"""
        selection = self.meeting_tree.selection()
        if selection:
            index = self.meeting_tree.index(selection[0])
            if index < len(self.records["meetings"]):
                meeting = self.records["meetings"][index]
                detail_window = tk.Toplevel(self.root)
                detail_window.title("会议详情")
                detail_window.geometry("600x400")
                
                text = scrolledtext.ScrolledText(detail_window, width=70, height=20)
                text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text.insert(tk.END, f"会议主题: {meeting.get('title', '')}\n")
                text.insert(tk.END, f"会议时间: {meeting.get('time', '')}\n")
                text.insert(tk.END, f"参会人员: {meeting.get('attendees', '')}\n")
                text.insert(tk.END, f"\n会议要点:\n{meeting.get('content', '')}")
                text.config(state=tk.DISABLED)
    
    def delete_meeting(self, event):
        """删除会议记录"""
        selection = self.meeting_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条会议记录吗？"):
                index = self.meeting_tree.index(selection[0])
                if index < len(self.records["meetings"]):
                    del self.records["meetings"][index]
                    self.save_records()
                    self.refresh_meeting_list()
    
    # 工作内容相关方法
    def save_work(self):
        """保存工作记录"""
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
        """清空工作输入"""
        self.work_title.delete(0, tk.END)
        self.work_date.delete(0, tk.END)
        self.work_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.work_content.delete("1.0", tk.END)
    
    def refresh_work_list(self):
        """刷新工作列表"""
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
        """显示工作详情"""
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
        """删除工作记录"""
        selection = self.work_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条工作记录吗？"):
                index = self.work_tree.index(selection[0])
                if index < len(self.records["works"]):
                    del self.records["works"][index]
                    self.save_records()
                    self.refresh_work_list()
    
    # 工作细节相关方法
    def save_detail(self):
        """保存工作细节"""
        title = self.detail_title.get().strip()
        time = self.detail_time.get().strip()
        content = self.detail_content.get("1.0", tk.END).strip()
        
        if not title or not content:
            messagebox.showwarning("警告", "请填写细节主题和详细内容！")
            return
        
        detail = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "time": time,
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        
        self.records["details"].insert(0, detail)
        self.save_records()
        self.refresh_detail_list()
        self.clear_detail()
        messagebox.showinfo("成功", "工作细节已保存！")
    
    def clear_detail(self):
        """清空细节输入"""
        self.detail_title.delete(0, tk.END)
        self.detail_time.delete(0, tk.END)
        self.detail_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.detail_content.delete("1.0", tk.END)
    
    def refresh_detail_list(self):
        """刷新细节列表"""
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
        """显示细节详情"""
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
        """删除细节记录"""
        selection = self.detail_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条细节记录吗？"):
                index = self.detail_tree.index(selection[0])
                if index < len(self.records["details"]):
                    del self.records["details"][index]
                    self.save_records()
                    self.refresh_detail_list()
    
    # 改进建议相关方法
    def save_improvement(self):
        """保存改进建议"""
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
        """清空改进输入"""
        self.improvement_title.delete(0, tk.END)
        self.improvement_date.delete(0, tk.END)
        self.improvement_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.improvement_content.delete("1.0", tk.END)
        self.improvement_status.set("待处理")
    
    def refresh_improvement_list(self):
        """刷新改进列表"""
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
        """显示改进详情"""
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
        """删除改进记录"""
        selection = self.improvement_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这条改进记录吗？"):
                index = self.improvement_tree.index(selection[0])
                if index < len(self.records["improvements"]):
                    del self.records["improvements"][index]
                    self.save_records()
                    self.refresh_improvement_list()
    
    # 会议提醒相关方法
    def add_reminder(self):
        """添加会议提醒"""
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
        """清空提醒输入"""
        self.reminder_title.delete(0, tk.END)
        self.reminder_time.delete(0, tk.END)
        self.reminder_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.reminder_note.delete(0, tk.END)
    
    def refresh_reminder_list(self):
        """刷新提醒列表"""
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
        """删除提醒"""
        selection = self.reminder_tree.selection()
        if selection:
            if messagebox.askyesno("确认", "确定要删除这个提醒吗？"):
                index = self.reminder_tree.index(selection[0])
                if index < len(self.config["reminders"]):
                    del self.config["reminders"][index]
                    self.save_config()
                    self.refresh_reminder_list()
    
    def start_reminder_service(self):
        """启动提醒服务"""
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
                                    # 触发提醒
                                    self.show_reminder_popup(reminder)
                                    reminder["notified"] = True
                                    self.save_config()
                            except Exception as e:
                                print(f"提醒检查错误: {e}")
                    
                    time.sleep(30)  # 每30秒检查一次
                except Exception as e:
                    print(f"提醒服务错误: {e}")
                    time.sleep(30)
        
        self.reminder_thread = threading.Thread(target=check_reminders, daemon=True)
        self.reminder_thread.start()
    
    def show_reminder_popup(self, reminder):
        """显示提醒弹窗"""
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
        """窗口关闭事件"""
        self.reminder_running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = WorkAssistant(root)
    root.mainloop()


if __name__ == "__main__":
    main()