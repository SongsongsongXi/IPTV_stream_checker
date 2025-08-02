#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直播源检测工具 - 中文GUI版本
功能：检测M3U文件中的直播源可用性，支持多种格式
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import urllib.request
import urllib.error
import re
import csv
import json
import threading
import time
from datetime import datetime
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

class StreamChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("直播源检测工具 v2.0")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 设置窗口图标和编码
        try:
            self.root.tk.call('encoding', 'system', 'utf-8')
        except:
            pass
            
        # 变量初始化
        self.channels = []
        self.valid_channels = []
        self.invalid_channels = []
        self.is_checking = False
        self.check_thread = None
        self.progress_queue = queue.Queue()
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
        # 启动进度更新
        self.update_progress()
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure('Title.TLabel', font=('微软雅黑', 12, 'bold'))
        style.configure('Header.TLabel', font=('微软雅黑', 10, 'bold'))
        style.configure('Custom.TButton', font=('微软雅黑', 9))
        
    def create_widgets(self):
        """创建界面组件"""
        # 主标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=5)
        
        title_label = ttk.Label(title_frame, text="直播源检测工具", style='Title.TLabel')
        title_label.pack()
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(self.root, text="文件选择", padding=10)
        file_frame.pack(fill='x', padx=10, pady=5)
        
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly')
        file_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        select_btn = ttk.Button(file_frame, text="选择M3U文件", command=self.select_file, style='Custom.TButton')
        select_btn.pack(side='right')
        
        # 检测选项区域
        options_frame = ttk.LabelFrame(self.root, text="检测选项", padding=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        # 第一行选项
        options_row1 = ttk.Frame(options_frame)
        options_row1.pack(fill='x', pady=(0, 5))
        
        ttk.Label(options_row1, text="超时时间(秒):").pack(side='left')
        self.timeout_var = tk.StringVar(value="10")
        timeout_spin = ttk.Spinbox(options_row1, from_=5, to=60, width=8, textvariable=self.timeout_var)
        timeout_spin.pack(side='left', padx=(5, 20))
        
        ttk.Label(options_row1, text="并发数:").pack(side='left')
        self.threads_var = tk.StringVar(value="20")
        threads_spin = ttk.Spinbox(options_row1, from_=1, to=50, width=8, textvariable=self.threads_var)
        threads_spin.pack(side='left', padx=(5, 20))
        
        # 第二行选项
        options_row2 = ttk.Frame(options_frame)
        options_row2.pack(fill='x')
        
        self.check_method_var = tk.StringVar(value="HEAD")
        ttk.Label(options_row2, text="检测方法:").pack(side='left')
        method_combo = ttk.Combobox(options_row2, textvariable=self.check_method_var, 
                                   values=["HEAD", "GET", "混合"], width=10, state='readonly')
        method_combo.pack(side='left', padx=(5, 20))
        
        self.retry_var = tk.BooleanVar(value=True)
        retry_check = ttk.Checkbutton(options_row2, text="失败重试", variable=self.retry_var)
        retry_check.pack(side='left', padx=(0, 20))
        
        self.detail_log_var = tk.BooleanVar(value=False)
        detail_check = ttk.Checkbutton(options_row2, text="详细日志", variable=self.detail_log_var)
        detail_check.pack(side='left')
        
        # 控制按钮区域
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="开始检测", command=self.start_check, style='Custom.TButton')
        self.start_btn.pack(side='left', padx=(0, 10))
        
        self.stop_btn = ttk.Button(control_frame, text="停止检测", command=self.stop_check, 
                                  style='Custom.TButton', state='disabled')
        self.stop_btn.pack(side='left', padx=(0, 10))
        
        self.export_btn = ttk.Button(control_frame, text="导出结果", command=self.export_results, 
                                    style='Custom.TButton', state='disabled')
        self.export_btn.pack(side='left', padx=(0, 10))
        
        clear_btn = ttk.Button(control_frame, text="清空日志", command=self.clear_log, style='Custom.TButton')
        clear_btn.pack(side='left')
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(self.root, text="检测进度", padding=10)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
        progress_info_frame = ttk.Frame(progress_frame)
        progress_info_frame.pack(fill='x')
        
        self.progress_label = ttk.Label(progress_info_frame, text="准备就绪")
        self.progress_label.pack(side='left')
        
        self.stats_label = ttk.Label(progress_info_frame, text="")
        self.stats_label.pack(side='right')
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(self.root, text="检测日志", padding=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True)
        
        # 添加欢迎信息
        self.log_message("欢迎使用直播源检测工具！", "INFO")
        self.log_message("请选择M3U文件开始检测", "INFO")
        
    def select_file(self):
        """选择M3U文件"""
        file_path = filedialog.askopenfilename(
            title="选择直播源文件",
            filetypes=[
                ("所有支持格式", "*.m3u;*.txt;*.csv"), 
                ("M3U文件", "*.m3u"), 
                ("文本文件", "*.txt"), 
                ("CSV文件", "*.csv"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.load_channels(file_path)
            
    def load_channels(self, file_path):
        """加载频道列表"""
        try:
            self.channels = []
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            lines = content.strip().split('\n')
            current_channel = None
            
            # 检测文件格式
            is_m3u = content.startswith('#EXTM3U') or any(line.startswith('#EXTINF:') for line in lines[:10])
            is_csv = not is_m3u and any(',' in line and line.count(',') >= 1 for line in lines[:10])
            
            if is_m3u:
                # 解析M3U文件
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#EXTM3U'):
                        continue
                        
                    if line.startswith('#EXTINF:'):
                        # 解析频道信息
                        # 格式1: #EXTINF:-1 tvg-name="..." group-title="...",频道名称
                        # 格式2: #EXTINF:-1,频道名称
                        match = re.search(r'#EXTINF:.*?,(.+)$', line)
                        if match:
                            name = match.group(1).strip()
                            current_channel = {'name': name, 'url': ''}
                            
                            # 尝试提取分组信息
                            group_match = re.search(r'group-title="([^"]*)"', line)
                            if group_match:
                                current_channel['group'] = group_match.group(1)
                            else:
                                current_channel['group'] = '未分类'
                                
                    elif line.startswith('http') and current_channel:
                        current_channel['url'] = line
                        self.channels.append(current_channel)
                        current_channel = None
                    elif line.startswith('http'):
                        # 没有EXTINF的URL
                        self.channels.append({
                            'name': f'频道_{len(self.channels)+1}',
                            'url': line,
                            'group': '未分类'
                        })
                        
            elif is_csv:
                # 解析CSV格式：频道名,URL
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    # 处理逗号分隔的格式
                    parts = line.split(',', 1)  # 只分割第一个逗号
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        url = parts[1].strip()
                        
                        if url.startswith('http'):
                            self.channels.append({
                                'name': name if name else f'频道_{line_num}',
                                'url': url,
                                'group': '未分类'
                            })
                    elif line.startswith('http'):
                        # 只有URL的行
                        self.channels.append({
                            'name': f'频道_{line_num}',
                            'url': line,
                            'group': '未分类'
                        })
                        
            else:
                # 解析纯URL列表
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if line.startswith('http'):
                        self.channels.append({
                            'name': f'频道_{line_num}',
                            'url': line,
                            'group': '未分类'
                        })
                    
            self.log_message(f"成功加载 {len(self.channels)} 个频道", "SUCCESS")
            if is_csv:
                self.log_message("检测到CSV格式文件", "INFO")
            elif is_m3u:
                self.log_message("检测到M3U格式文件", "INFO")
            else:
                self.log_message("检测到URL列表格式文件", "INFO")
            
        except Exception as e:
            self.log_message(f"加载文件失败: {str(e)}", "ERROR")
            messagebox.showerror("错误", f"加载文件失败:\n{str(e)}")
            
    def start_check(self):
        """开始检测"""
        if not self.channels:
            messagebox.showwarning("警告", "请先选择并加载M3U文件")
            return
            
        if self.is_checking:
            return
            
        self.is_checking = True
        self.valid_channels = []
        self.invalid_channels = []
        
        # 更新按钮状态
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.export_btn.config(state='disabled')
        
        # 重置进度
        self.progress_var.set(0)
        self.progress_label.config(text="开始检测...")
        
        # 清空之前的结果
        self.log_message("=" * 50, "INFO")
        self.log_message("开始检测直播源...", "INFO")
        self.log_message(f"总计 {len(self.channels)} 个频道", "INFO")
        self.log_message(f"超时设置: {self.timeout_var.get()}秒", "INFO")
        self.log_message(f"并发数: {self.threads_var.get()}", "INFO")
        self.log_message(f"检测方法: {self.check_method_var.get()}", "INFO")
        self.log_message("=" * 50, "INFO")
        
        # 启动检测线程
        self.check_thread = threading.Thread(target=self.check_channels)
        self.check_thread.daemon = True
        self.check_thread.start()
        
    def stop_check(self):
        """停止检测"""
        self.is_checking = False
        self.progress_queue.put(('status', '正在停止检测...'))
        
    def check_channels(self):
        """检测频道可用性"""
        timeout = int(self.timeout_var.get())
        max_workers = int(self.threads_var.get())
        method = self.check_method_var.get()
        retry = self.retry_var.get()
        
        completed = 0
        total = len(self.channels)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_channel = {
                executor.submit(self.check_single_channel, channel, timeout, method, retry): channel 
                for channel in self.channels
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_channel):
                if not self.is_checking:
                    break
                    
                channel = future_to_channel[future]
                try:
                    result = future.result()
                    completed += 1
                    
                    if result['status'] == 'valid':
                        self.valid_channels.append(result)
                        self.progress_queue.put(('valid', result))
                    else:
                        self.invalid_channels.append(result)
                        if self.detail_log_var.get():
                            self.progress_queue.put(('invalid', result))
                    
                    # 更新进度
                    progress = (completed / total) * 100
                    self.progress_queue.put(('progress', {
                        'progress': progress,
                        'completed': completed,
                        'total': total,
                        'valid': len(self.valid_channels),
                        'invalid': len(self.invalid_channels)
                    }))
                    
                except Exception as e:
                    completed += 1
                    self.progress_queue.put(('error', f"检测频道 {channel['name']} 时出错: {str(e)}"))
        
        # 检测完成
        self.progress_queue.put(('complete', None))
        
    def check_single_channel(self, channel, timeout, method, retry):
        """检测单个频道"""
        name = channel['name']
        url = channel['url']
        group = channel.get('group', '未分类')
        
        max_retries = 2 if retry else 1
        
        for attempt in range(max_retries):
            try:
                if method == "HEAD":
                    response = requests.head(url, timeout=timeout, allow_redirects=True)
                elif method == "GET":
                    response = requests.get(url, timeout=timeout, stream=True)
                    # 只读取少量数据
                    for chunk in response.iter_content(chunk_size=1024):
                        break
                else:  # 混合方法
                    try:
                        response = requests.head(url, timeout=timeout//2, allow_redirects=True)
                    except:
                        response = requests.get(url, timeout=timeout, stream=True)
                        for chunk in response.iter_content(chunk_size=1024):
                            break
                
                if response.status_code == 200:
                    return {
                        'name': name,
                        'url': url,
                        'group': group,
                        'status': 'valid',
                        'status_code': response.status_code,
                        'response_time': 0  # 可以添加响应时间测量
                    }
                else:
                    if attempt == max_retries - 1:
                        return {
                            'name': name,
                            'url': url,
                            'group': group,
                            'status': 'invalid',
                            'error': f"HTTP {response.status_code}",
                            'status_code': response.status_code
                        }
                        
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    return {
                        'name': name,
                        'url': url,
                        'group': group,
                        'status': 'invalid',
                        'error': '连接超时'
                    }
            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        'name': name,
                        'url': url,
                        'group': group,
                        'status': 'invalid',
                        'error': str(e)
                    }
                    
        return {
            'name': name,
            'url': url,
            'group': group,
            'status': 'invalid',
            'error': '未知错误'
        }
        
    def update_progress(self):
        """更新进度显示"""
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()
                
                if msg_type == 'progress':
                    self.progress_var.set(data['progress'])
                    self.progress_label.config(text=f"检测进度: {data['completed']}/{data['total']}")
                    self.stats_label.config(text=f"有效: {data['valid']} | 无效: {data['invalid']}")
                    
                elif msg_type == 'valid':
                    if self.detail_log_var.get():
                        self.log_message(f"✓ {data['name']} - 可用", "SUCCESS")
                    
                elif msg_type == 'invalid':
                    error = data.get('error', '未知错误')
                    self.log_message(f"✗ {data['name']} - {error}", "ERROR")
                    
                elif msg_type == 'error':
                    self.log_message(data, "ERROR")
                    
                elif msg_type == 'status':
                    self.progress_label.config(text=data)
                    
                elif msg_type == 'complete':
                    self.check_complete()
                    break
                    
        except queue.Empty:
            pass
        
        # 继续更新
        self.root.after(100, self.update_progress)
        
    def check_complete(self):
        """检测完成处理"""
        self.is_checking = False
        
        # 更新按钮状态
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.export_btn.config(state='normal')
        
        # 显示结果
        total = len(self.channels)
        valid = len(self.valid_channels)
        invalid = len(self.invalid_channels)
        success_rate = (valid / total * 100) if total > 0 else 0
        
        self.progress_label.config(text="检测完成")
        self.stats_label.config(text=f"有效: {valid} | 无效: {invalid} | 成功率: {success_rate:.1f}%")
        
        self.log_message("=" * 50, "INFO")
        self.log_message("检测完成！", "SUCCESS")
        self.log_message(f"总计检测: {total} 个频道", "INFO")
        self.log_message(f"有效频道: {valid} 个", "SUCCESS")
        self.log_message(f"无效频道: {invalid} 个", "ERROR")
        self.log_message(f"成功率: {success_rate:.1f}%", "INFO")
        self.log_message("=" * 50, "INFO")
        
        # 显示完成对话框
        messagebox.showinfo("检测完成", 
                           f"检测完成！\n\n"
                           f"总计: {total} 个频道\n"
                           f"有效: {valid} 个\n"
                           f"无效: {invalid} 个\n"
                           f"成功率: {success_rate:.1f}%")
        
    def export_results(self):
        """导出结果"""
        if not self.valid_channels and not self.invalid_channels:
            messagebox.showwarning("警告", "没有检测结果可导出")
            return
            
        export_dir = filedialog.askdirectory(title="选择导出目录")
        if not export_dir:
            return
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 导出有效频道 (CSV)
            if self.valid_channels:
                valid_file = os.path.join(export_dir, f"有效频道_{timestamp}.csv")
                with open(valid_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['频道名称', 'URL', '分组'])
                    for channel in self.valid_channels:
                        writer.writerow([channel['name'], channel['url'], channel.get('group', '未分类')])
                
                # 同时导出M3U格式
                valid_m3u = os.path.join(export_dir, f"有效频道_{timestamp}.m3u")
                with open(valid_m3u, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    for channel in self.valid_channels:
                        group = channel.get('group', '未分类')
                        f.write(f'#EXTINF:-1 group-title="{group}",{channel["name"]}\n')
                        f.write(f'{channel["url"]}\n')
            
            # 导出无效频道 (CSV)
            if self.invalid_channels:
                invalid_file = os.path.join(export_dir, f"无效频道_{timestamp}.csv")
                with open(invalid_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['频道名称', 'URL', '分组', '错误信息'])
                    for channel in self.invalid_channels:
                        writer.writerow([
                            channel['name'], 
                            channel['url'], 
                            channel.get('group', '未分类'),
                            channel.get('error', '未知错误')
                        ])
            
            # 导出详细报告 (JSON)
            report_file = os.path.join(export_dir, f"检测报告_{timestamp}.json")
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_channels': len(self.channels),
                'valid_channels': len(self.valid_channels),
                'invalid_channels': len(self.invalid_channels),
                'success_rate': len(self.valid_channels) / len(self.channels) * 100 if self.channels else 0,
                'valid_list': self.valid_channels,
                'invalid_list': self.invalid_channels
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.log_message(f"结果已导出到: {export_dir}", "SUCCESS")
            messagebox.showinfo("导出完成", f"结果已成功导出到:\n{export_dir}")
            
        except Exception as e:
            self.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", f"导出失败:\n{str(e)}")
            
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("日志已清空", "INFO")
        
    def log_message(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 设置颜色
        colors = {
            "INFO": "black",
            "SUCCESS": "green",
            "ERROR": "red",
            "WARNING": "orange"
        }
        
        color = colors.get(level, "black")
        
        # 插入消息
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        
        # 设置颜色 (简化版本，tkinter的文本着色比较复杂)
        self.log_text.see(tk.END)

def main():
    """主函数"""
    root = tk.Tk()
    app = StreamChecker(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序出错: {str(e)}")

if __name__ == "__main__":
    main()
