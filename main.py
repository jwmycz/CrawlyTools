import wx
import wx.lib.scrolledpanel as scrolled
import time
import threading
import os
import shutil
import json
from core.crawler_manager import CrawlerManager
from utils.system_monitor import SystemMonitor
from utils.scheduler_manager import SchedulerManager

class CrawlerGUI(wx.Frame):
    def __init__(self):
        super().__init__(None, title="爬虫管理系统", size=(1200, 800))
        
        # 先初始化UI，显示界面
        self.init_ui()
        
        # 然后在后台线程中进行其他初始化操作
        self.crawler_manager = None
        self.system_monitor = None
        self.scheduler_manager = None
        
        # 启动后台初始化线程
        threading.Thread(target=self.init_background, daemon=True).start()
        
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_status, self.update_timer)
        self.update_timer.Start(1000)  # 每秒更新一次状态
    
    def init_background(self):
        """后台初始化操作"""
        print("开始后台初始化...")
        try:
            # 先初始化系统资源监控（确保优先可用）
            self.system_monitor = SystemMonitor()  # 初始化系统资源监控
            print("SystemMonitor初始化成功")
            
            # 然后初始化CrawlerManager
            self.crawler_manager = CrawlerManager()
            print("CrawlerManager初始化成功")
            
            # 初始化调度器
            print("开始初始化调度器...")
            self.scheduler_manager = SchedulerManager(self.crawler_manager)
            print("调度器实例创建成功")
            self.scheduler_manager.start()
            print("调度器启动成功")
            
            # 更新任务列表
            wx.CallAfter(self.update_task_list)
            print("后台初始化完成")
        except Exception as e:
            print(f"后台初始化失败: {e}")
            import traceback
            traceback.print_exc()
        
    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 顶部按钮栏
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.run_btn = wx.Button(panel, label="运行选中任务")
        self.stop_btn = wx.Button(panel, label="停止选中任务")
        self.clear_log_btn = wx.Button(panel, label="清空当前日志")
        self.schedule_btn = wx.Button(panel, label="定时设置")
        self.reload_btn = wx.Button(panel, label="重新加载模块")
        self.import_btn = wx.Button(panel, label="导入爬虫模块")
        
        button_sizer.Add(self.run_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.stop_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.clear_log_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.schedule_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.reload_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.import_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # 系统资源监控区域
        self.system_info_text = wx.StaticText(panel, label="系统资源监控: 正在初始化...")
        self.system_info_text.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(self.system_info_text, 0, wx.EXPAND | wx.ALL, 5)
        
        # 中间分割窗口
        splitter = wx.SplitterWindow(panel, style=wx.SP_3D)
        
        # 左侧任务列表
        left_panel = wx.Panel(splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.task_list = wx.ListCtrl(left_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.task_list.InsertColumn(0, "任务名", width=150)
        self.task_list.InsertColumn(1, "状态", width=100)
        self.task_list.InsertColumn(2, "上次运行时间", width=150)
        self.task_list.InsertColumn(3, "参数", width=300)
        
        left_sizer.Add(self.task_list, 1, wx.EXPAND | wx.ALL, 5)
        left_panel.SetSizer(left_sizer)
        
        # 右侧日志和参数设置
        right_panel = scrolled.ScrolledPanel(splitter, style=wx.SUNKEN_BORDER)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        

        
        # 日志显示区域
        log_box = wx.StaticBox(right_panel, label="任务日志")
        log_box_sizer = wx.StaticBoxSizer(log_box, wx.VERTICAL)
        
        self.log_text = wx.TextCtrl(right_panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(300, 300))
        log_box_sizer.Add(self.log_text, 1, wx.EXPAND | wx.ALL, 5)
        
        right_sizer.Add(log_box_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        # 错误信息区域
        error_box = wx.StaticBox(right_panel, label="错误信息")
        error_box_sizer = wx.StaticBoxSizer(error_box, wx.VERTICAL)
        
        self.error_text = wx.TextCtrl(right_panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(300, 100))
        error_box_sizer.Add(self.error_text, 1, wx.EXPAND | wx.ALL, 5)
        
        right_sizer.Add(error_box_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        right_panel.SetSizer(right_sizer)
        right_panel.SetAutoLayout(1)
        right_panel.SetupScrolling()
        
        # 设置分割窗口比例
        splitter.SplitVertically(left_panel, right_panel, 500)
        splitter.SetMinimumPaneSize(300)
        
        main_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
        
        # 绑定事件
        self.Bind(wx.EVT_BUTTON, self.on_run, self.run_btn)
        self.Bind(wx.EVT_BUTTON, self.on_stop, self.stop_btn)
        self.Bind(wx.EVT_BUTTON, self.on_clear_log, self.clear_log_btn)
        self.Bind(wx.EVT_BUTTON, self.on_schedule, self.schedule_btn)
        self.Bind(wx.EVT_BUTTON, self.on_reload, self.reload_btn)
        self.Bind(wx.EVT_BUTTON, self.on_import, self.import_btn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_task_selected, self.task_list)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_task_double_clicked, self.task_list)  # 双击事件
        self.task_list.Bind(wx.EVT_CONTEXT_MENU, self.on_task_right_clicked)  # 右键菜单事件
    
    def update_task_list(self):
        self.task_list.DeleteAllItems()
        crawlers = self.crawler_manager.get_crawlers()
        for task_name, crawler in crawlers.items():
            index = self.task_list.InsertItem(self.task_list.GetItemCount(), task_name)
            self.task_list.SetItem(index, 1, crawler.status)
            self.task_list.SetItem(index, 2, crawler.last_run_time or "-")
            params = self.task_params.get(task_name, "")
            # 显示参数的简要信息，过长时截断
            display_params = params[:50] + "..." if len(params) > 50 else params
            self.task_list.SetItem(index, 3, display_params)
    
    def update_status(self, event):
        """更新任务状态和系统资源信息"""
        # 更新系统资源监控信息（独立于crawler_manager状态）
        if self.system_monitor:
            system_info = self.system_monitor.get_system_info_string()
            self.system_info_text.SetLabel(f"系统资源监控: {system_info}")
        
        # 更新任务状态（需要crawler_manager）
        if self.crawler_manager:
            # 更新任务列表
            crawlers = self.crawler_manager.get_crawlers()
            for i in range(self.task_list.GetItemCount()):
                task_name = self.task_list.GetItem(i, 0).GetText()
                crawler = crawlers.get(task_name)
                if crawler:
                    self.task_list.SetItem(i, 1, crawler.status)
                    self.task_list.SetItem(i, 2, crawler.last_run_time or "-")
            
            # 更新当前选中任务的日志和错误信息
            selected = self.task_list.GetFirstSelected()
            if selected != -1:
                task_name = self.task_list.GetItem(selected, 0).GetText()
                self.update_logs(task_name)
    
    def on_run(self, event):
        """运行选中任务"""
        selected = self.task_list.GetFirstSelected()
        if selected != -1:
            task_name = self.task_list.GetItem(selected, 0).GetText()
            # 获取任务特定参数
            params_text = self.task_params.get(task_name, "").strip()
            params = {}
            if params_text:
                try:
                    # 检查是否为直接的命令行参数字符串，如"--env ly --debug"
                    if params_text.strip().startswith("--"):
                        # 直接作为__args__参数
                        params["__args__"] = params_text.strip()
                    else:
                        # 尝试解析为字典
                        import ast
                        try:
                            params = ast.literal_eval(params_text)
                            if not isinstance(params, dict):
                                params = {}
                        except:
                            # 解析为key=value格式
                            for param in params_text.split(","):
                                if "=" in param:
                                    key, value = param.split("=", 1)
                                    params[key.strip()] = value.strip()
                                else:
                                    # 单个值，如--verbose
                                    key = param.strip()
                                    if key.startswith("--"):
                                        params[key] = ""
                                    else:
                                        params[key] = ""
                except:
                    wx.MessageBox("参数格式错误，支持格式：\n1. key1=value1,key2=value2\n2. --env ly --debug\n3. {\"key\": \"value\"}", "错误", wx.OK | wx.ICON_ERROR)
                    return
            
            if self.crawler_manager.run_crawler(task_name, params):
                wx.MessageBox(f"任务 {task_name} 已启动", "提示", wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox(f"任务 {task_name} 启动失败，可能正在运行", "错误", wx.OK | wx.ICON_ERROR)
    
    def on_stop(self, event):
        """停止选中任务"""
        selected = self.task_list.GetFirstSelected()
        if selected != -1:
            task_name = self.task_list.GetItem(selected, 0).GetText()
            if self.crawler_manager.stop_crawler(task_name):
                wx.MessageBox(f"任务 {task_name} 已停止", "提示", wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox(f"任务 {task_name} 停止失败", "错误", wx.OK | wx.ICON_ERROR)
    
    def on_reload(self, event):
        """重新加载模块"""
        self.crawler_manager.reload_crawlers()
        self.update_task_list()
        wx.MessageBox("模块已重新加载", "提示", wx.OK | wx.ICON_INFORMATION)
    
    def on_import(self, event):
        """导入爬虫模块或项目"""
        # 创建导入类型选择对话框
        dialog = wx.Dialog(self, title="选择导入类型", size=(300, 200))
        panel = wx.Panel(dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 标题
        title = wx.StaticText(panel, label="请选择导入类型:")
        sizer.Add(title, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        # 单选按钮
        self.import_type = wx.RadioBox(panel, label="导入类型", choices=["单个Python文件", "项目压缩包(.zip)", "项目目录"],
                                      majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        sizer.Add(self.import_type, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        # 按钮
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK, label="确定")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="取消")
        btn_sizer.Add(ok_btn, 0, wx.ALL, 5)
        btn_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        
        panel.SetSizer(sizer)
        
        if dialog.ShowModal() == wx.ID_OK:
            import_type = self.import_type.GetSelection()
            dialog.Destroy()
            
            try:
                if import_type == 0:  # 单个Python文件
                    self.import_single_file()
                elif import_type == 1:  # 项目压缩包
                    self.import_project_zip()
                elif import_type == 2:  # 项目目录
                    self.import_project_directory()
            except Exception as e:
                wx.MessageBox(f"导入失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
        else:
            dialog.Destroy()
    
    def on_task_selected(self, event):
        """选中任务时更新日志和错误信息"""
        task_name = event.GetItem().GetText()
        self.update_logs(task_name)
        
    def validate_python_file(self, file_path):
        """验证Python文件的有效性"""
        try:
            # 检查文件是否包含有效的Python语法
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试编译文件内容以检查语法错误
            compile(content, file_path, 'exec')
            
            # 检查是否是有效的爬虫文件
            if 'BaseCrawler' in content or 'BlockingScheduler' in content:
                return True, "有效爬虫文件"
            else:
                # 即使不是标准爬虫文件，也允许导入作为自定义脚本
                return True, "自定义脚本文件"
                
        except SyntaxError as e:
            return False, f"Python语法错误: {e}"
        except Exception as e:
            return False, f"文件验证失败: {e}"
    
    def import_single_file(self):
        """导入单个Python文件"""
        with wx.FileDialog(self, "选择爬虫模块文件", wildcard="Python files (*.py)|*.py",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            path = fileDialog.GetPath()
            try:
                # 验证文件
                is_valid, message = self.validate_python_file(path)
                if not is_valid:
                    wx.MessageBox(f"文件无效: {message}", "错误", wx.OK | wx.ICON_ERROR)
                    return
                
                # 获取文件所在目录
                file_dir = os.path.dirname(path)
                file_name = os.path.basename(path)
                
                # 生成项目名（使用文件名作为项目名）
                project_name = os.path.splitext(file_name)[0]
                
                # 目标目录：crawlers/项目名
                dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawlers", project_name)
                
                # 检查目标目录是否存在
                if os.path.exists(dest_dir):
                    dlg = wx.MessageDialog(self, f"项目 {project_name} 已存在，是否覆盖？", 
                                          "询问", wx.YES_NO | wx.ICON_QUESTION)
                    result = dlg.ShowModal()
                    dlg.Destroy()
                    if result == wx.ID_NO:
                        return
                    # 删除现有目录
                    shutil.rmtree(dest_dir)
                
                # 复制整个目录结构
                shutil.copytree(file_dir, dest_dir)
                
                # 获取运行文件相对于项目根的路径
                run_file = file_name
                
                # 创建项目配置文件，记录运行文件
                config_file = os.path.join(dest_dir, "project_config.json")
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "run_file": run_file,
                        "project_name": project_name
                    }, f)
                
                # 重新加载模块
                self.crawler_manager.reload_crawlers()
                self.update_task_list()
                wx.MessageBox("爬虫模块导入成功", "提示", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"导入失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
                raise
                
    def import_project_zip(self):
        """导入项目压缩包"""
        with wx.FileDialog(self, "选择项目压缩包", wildcard="Zip files (*.zip)|*.zip",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            path = fileDialog.GetPath()
            try:
                import zipfile
                import os
                import shutil
                from pathlib import Path
                
                # 创建临时目录
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    # 解压zip文件
                    with zipfile.ZipFile(path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # 获取解压后的内容
                    contents = os.listdir(temp_dir)
                    if len(contents) == 1 and os.path.isdir(os.path.join(temp_dir, contents[0])):
                        # 如果zip包含一个根目录，使用该目录作为项目根
                        project_dir = os.path.join(temp_dir, contents[0])
                    else:
                        # 否则使用临时目录作为项目根
                        project_dir = temp_dir
                    
                    # 让用户选择运行文件
                    run_file = self.select_run_file(project_dir)
                    if not run_file:
                        return
                    
                    # 获取运行文件相对于项目根的路径
                    relative_path = os.path.relpath(run_file, project_dir)
                    
                    # 目标目录：crawlers/项目名
                    project_name = os.path.basename(project_dir)
                    dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawlers", project_name)
                    
                    # 检查目标目录是否存在
                    if os.path.exists(dest_dir):
                        dlg = wx.MessageDialog(self, f"项目 {project_name} 已存在，是否覆盖？", 
                                              "询问", wx.YES_NO | wx.ICON_QUESTION)
                        result = dlg.ShowModal()
                        dlg.Destroy()
                        if result == wx.ID_NO:
                            return
                        # 删除现有目录
                        shutil.rmtree(dest_dir)
                    
                    # 复制整个项目目录
                    shutil.copytree(project_dir, dest_dir)
                    
                    # 创建项目配置文件，记录运行文件
                    config_file = os.path.join(dest_dir, "project_config.json")
                    import json
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "run_file": relative_path,
                            "project_name": project_name
                        }, f)
                
                # 重新加载模块
                self.crawler_manager.reload_crawlers()
                self.update_task_list()
                
                wx.MessageBox(f"项目 {project_name} 导入成功！", "提示", wx.OK | wx.ICON_INFORMATION)
                    
            except Exception as e:
                wx.MessageBox(f"导入失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
                raise
                
    def select_run_file(self, project_dir):
        """让用户选择项目的运行文件"""
        # 获取项目中所有的.py文件
        all_py_files = []
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, project_dir)
                    all_py_files.append((relative_path, file_path))
        
        if not all_py_files:
            wx.MessageBox("项目中未找到Python文件", "错误", wx.OK | wx.ICON_ERROR)
            return None
        
        # 创建选择对话框
        dialog = wx.Dialog(self, title="选择运行文件", size=(400, 300))
        panel = wx.Panel(dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 文件列表
        list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        list_ctrl.InsertColumn(0, "文件路径", width=350)
        
        for i, (relative_path, file_path) in enumerate(all_py_files):
            list_ctrl.InsertItem(i, relative_path)
        
        sizer.Add(list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        
        # 按钮
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK, label="确定")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="取消")
        btn_sizer.Add(ok_btn, 0, wx.ALL, 5)
        btn_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 5)
        panel.SetSizer(sizer)
        
        if dialog.ShowModal() == wx.ID_OK:
            selected_index = list_ctrl.GetFirstSelected()
            if selected_index != -1:
                _, file_path = all_py_files[selected_index]
                dialog.Destroy()
                return file_path
        
        dialog.Destroy()
        return None
    
    def import_project_directory(self):
        """导入项目目录"""
        with wx.DirDialog(self, "选择项目目录", style=wx.DD_DEFAULT_STYLE) as dirDialog:
            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            path = dirDialog.GetPath()
            try:
                import os
                import shutil
                import json
                
                # 让用户选择运行文件
                run_file = self.select_run_file(path)
                if not run_file:
                    return
                
                # 获取运行文件相对于项目根的路径
                project_dir = path
                relative_path = os.path.relpath(run_file, project_dir)
                
                # 目标目录：crawlers/项目名
                project_name = os.path.basename(project_dir)
                dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawlers", project_name)
                
                # 检查目标目录是否存在
                if os.path.exists(dest_dir):
                    dlg = wx.MessageDialog(self, f"项目 {project_name} 已存在，是否覆盖？", 
                                          "询问", wx.YES_NO | wx.ICON_QUESTION)
                    result = dlg.ShowModal()
                    dlg.Destroy()
                    if result == wx.ID_NO:
                        return
                    # 删除现有目录
                    shutil.rmtree(dest_dir)
                
                # 复制整个项目目录
                shutil.copytree(project_dir, dest_dir)
                
                # 创建项目配置文件，记录运行文件
                config_file = os.path.join(dest_dir, "project_config.json")
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "run_file": relative_path,
                        "project_name": project_name
                    }, f)
                
                # 重新加载模块
                self.crawler_manager.reload_crawlers()
                self.update_task_list()
                
                wx.MessageBox(f"项目 {project_name} 导入成功！", "提示", wx.OK | wx.ICON_INFORMATION)
                    
            except Exception as e:
                wx.MessageBox(f"导入失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
                raise
    
    def on_task_right_clicked(self, event):
        """任务列表右键菜单"""
        # 获取右键点击的位置
        pos = event.GetPosition()
        # 转换为任务列表中的索引
        item, flags = self.task_list.HitTest(pos)
        if item != -1:
            # 创建右键菜单
            menu = wx.Menu()
            edit_params_menu = menu.Append(wx.ID_ANY, "编辑参数")
            run_menu = menu.Append(wx.ID_ANY, "运行任务")
            stop_menu = menu.Append(wx.ID_ANY, "停止任务")
            
            # 获取任务名
            task_name = self.task_list.GetItem(item, 0).GetText()
            
            # 绑定事件
            self.Bind(wx.EVT_MENU, lambda e: self.on_edit_params(task_name), edit_params_menu)
            self.Bind(wx.EVT_MENU, lambda e: self.on_run_task_from_menu(task_name), run_menu)
            self.Bind(wx.EVT_MENU, lambda e: self.on_stop_task_from_menu(task_name), stop_menu)
            
            # 显示菜单
            self.task_list.PopupMenu(menu, pos)
            menu.Destroy()
    
    def on_task_double_clicked(self, event):
        """双击任务时编辑参数"""
        task_name = event.GetItem().GetText()
        self.on_edit_params(task_name)
    
    def on_edit_params(self, task_name):
        """编辑任务参数"""
        # 获取当前参数
        current_params = self.task_params.get(task_name, "")
        
        # 创建参数编辑对话框
        dialog = wx.Dialog(self, title=f"编辑任务参数 - {task_name}", size=(400, 200))
        panel = wx.Panel(dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 参数输入框
        param_label = wx.StaticText(panel, label="参数设置:")
        sizer.Add(param_label, 0, wx.ALL, 5)
        
        param_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(380, 100))
        param_text.SetValue(current_params)
        sizer.Add(param_text, 1, wx.EXPAND | wx.ALL, 5)
        
        # 提示文本
        hint_text = wx.StaticText(panel, label="支持格式：\n1. key1=value1,key2=value2\n2. --env ly --debug\n3. {\"key\": \"value\"}")
        hint_text.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(hint_text, 0, wx.ALL, 5)
        
        # 按钮
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, wx.ID_OK, label="确定")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="取消")
        button_sizer.Add(ok_btn, 0, wx.ALL, 5)
        button_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        panel.SetSizer(sizer)
        
        if dialog.ShowModal() == wx.ID_OK:
            # 保存参数
            new_params = param_text.GetValue()
            self.task_params[task_name] = new_params
            # 更新任务列表中的参数显示
            self.update_task_list()
        
        dialog.Destroy()
    
    def on_run_task_from_menu(self, task_name):
        """从右键菜单运行任务"""
        # 设置选中项
        for i in range(self.task_list.GetItemCount()):
            if self.task_list.GetItem(i, 0).GetText() == task_name:
                self.task_list.Select(i)
                break
        # 调用运行函数
        self.on_run(None)
    
    def on_stop_task_from_menu(self, task_name):
        """从右键菜单停止任务"""
        # 调用停止函数
        self.on_stop(None)
    
    def update_logs(self, task_name):
        """更新选中任务的日志和错误信息"""
        if not self.crawler_manager:
            return
            
        current_time = time.time() * 1000  # 毫秒
        
        # 如果距离上次更新不足指定时间，并且没有请求更新，则延迟更新
        if current_time - self.last_log_update_time < self.log_update_interval and not self.log_update_requested:
            self.log_update_requested = True
            return
            
        # 更新当前日志任务
        self.current_log_task = task_name
        self.last_log_update_time = current_time
        self.log_update_requested = False
        
        # 在后台线程中获取日志内容，避免阻塞主线程
        def get_logs_in_background():
            try:
                # 只获取最新的200行日志，避免内存占用过大
                logs = self.crawler_manager.log_manager.get_log_content(task_name, max_lines=200)
                crawler = self.crawler_manager.get_crawler(task_name)
                error_info = crawler.error_info if (crawler and crawler.error_info) else ""
                
                # 确保当前任务仍是选中的任务
                if self.current_log_task == task_name:
                    wx.CallAfter(self.update_logs_ui, logs, error_info)
            except Exception as e:
                print(f"获取日志内容失败: {e}")
        
        threading.Thread(target=get_logs_in_background, daemon=True).start()
    
    def update_logs_ui(self, logs, error_info):
        """在主线程中更新日志UI"""
        self.log_text.SetValue(logs)
        # 滚动到底部
        self.log_text.SetInsertionPointEnd()
        
        self.error_text.SetValue(error_info)
    
    def __init__(self):
        super().__init__(None, title="爬虫管理系统", size=(1000, 700))
        
        # 先初始化UI，显示界面
        self.init_ui()
        
        # 然后在后台线程中进行其他初始化操作
        self.crawler_manager = None
        self.system_monitor = None
        self.scheduler_manager = None
        
        # 日志更新节流机制
        self.last_log_update_time = 0
        self.log_update_interval = 1000  # 1秒更新一次日志
        self.log_update_requested = False
        self.current_log_task = None
        
        # 存储每个任务的参数
        self.task_params = {}
        
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_status, self.update_timer)
        self.update_timer.Start(1000)  # 每秒更新一次状态
        
        # 启动后台初始化线程
        threading.Thread(target=self.init_background, daemon=True).start()
    
    def on_clear_log(self, event):
        """清空当前选中任务的日志"""
        selected = self.task_list.GetFirstSelected()
        if selected != -1:
            task_name = self.task_list.GetItem(selected, 0).GetText()
            # 清空日志文件
            self.crawler_manager.log_manager.clear_log(task_name)
            # 更新日志显示
            self.log_text.SetValue("")
            wx.MessageBox(f"已清空 {task_name} 的日志", "提示", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox("请先选中一个任务", "提示", wx.OK | wx.ICON_INFORMATION)
    

    
    def on_schedule(self, event):
        """显示统一的定时任务管理对话框"""
        # 获取选中的任务名（如果有）
        selected = self.task_list.GetFirstSelected()
        selected_task = None
        if selected != -1:
            selected_task = self.task_list.GetItem(selected, 0).GetText()
        
        # 显示统一的定时任务管理对话框，即使调度器尚未初始化
        # 对话框内部会处理调度器初始化
        dialog = ScheduleManagementDialog(self, self.scheduler_manager, self.crawler_manager, selected_task)
        dialog.ShowModal()
        dialog.Destroy()
    

    
    def on_close(self, event):
        """关闭窗口时停止所有爬虫和调度器"""
        # 停止所有爬虫
        if self.crawler_manager:
            for crawler in self.crawler_manager.get_crawlers().values():
                crawler.stop()
        # 停止调度器
        if self.scheduler_manager:
            self.scheduler_manager.stop()
        self.Destroy()

class ScheduleManagementDialog(wx.Dialog):
    """统一的定时任务管理对话框"""
    def __init__(self, parent, scheduler_manager, crawler_manager, selected_task=None):
        super().__init__(parent, title="定时任务管理", size=(800, 500))
        self.scheduler_manager = scheduler_manager
        self.crawler_manager = crawler_manager
        self.db_manager = crawler_manager.db_manager
        self.selected_task = selected_task
        self.init_ui()
        
        # 显示加载提示
        self.schedule_list.InsertItem(0, "正在加载定时任务...")
        self.schedule_list.SetItem(0, 1, "")
        self.schedule_list.SetItem(0, 2, "")
        self.schedule_list.SetItem(0, 3, "")
        self.schedule_list.SetItem(0, 4, "")
        self.schedule_list.SetItem(0, 5, "")
        
        # 在后台线程中初始化调度器和刷新任务列表
        threading.Thread(target=self.init_scheduler_and_refresh, daemon=True).start()
    
    def init_scheduler_and_refresh(self):
        """在后台线程中初始化调度器和刷新任务列表"""
        print("初始化调度器和刷新任务列表开始")
        
        # 先初始化调度器
        print("开始初始化调度器")
        self.init_scheduler_in_background()
        
        # 然后刷新任务列表
        print("开始刷新任务列表")
        self.refresh_task_list_in_background()
    
    def init_scheduler_in_background(self):
        """在后台线程中初始化调度器"""
        if not self.scheduler_manager:
            try:
                # 如果调度器未初始化，创建新的调度器实例
                print("调度器未初始化，正在创建新的调度器实例")
                from utils.scheduler_manager import SchedulerManager
                self.scheduler_manager = SchedulerManager(self.crawler_manager)
                self.scheduler_manager.start()
                print("调度器已成功初始化")
            except Exception as e:
                print(f"调度器初始化失败: {e}")
                # 即使调度器初始化失败，也继续执行，确保UI能显示任务列表
                wx.CallAfter(wx.MessageBox, f"调度器初始化失败: {e}", "警告", wx.OK | wx.ICON_WARNING)
    
    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 顶部按钮栏
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.add_btn = wx.Button(panel, label="添加定时任务")
        self.edit_btn = wx.Button(panel, label="编辑选中任务")
        self.delete_btn = wx.Button(panel, label="删除选中任务")
        self.refresh_btn = wx.Button(panel, label="刷新任务列表")
        
        button_sizer.Add(self.add_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.edit_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.delete_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.refresh_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # 定时任务列表
        self.schedule_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.LC_VRULES)
        
        # 添加列
        self.schedule_list.InsertColumn(0, "任务名", width=150)
        self.schedule_list.InsertColumn(1, "Cron表达式", width=150)
        self.schedule_list.InsertColumn(2, "状态", width=80)
        self.schedule_list.InsertColumn(3, "参数", width=200)
        self.schedule_list.InsertColumn(4, "上次运行", width=150)
        self.schedule_list.InsertColumn(5, "下次运行", width=150)
        
        main_sizer.Add(self.schedule_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # 底部关闭按钮
        close_btn = wx.Button(panel, label="关闭")
        main_sizer.Add(close_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        panel.SetSizer(main_sizer)
        
        # 绑定事件
        self.Bind(wx.EVT_BUTTON, self.on_add, self.add_btn)
        self.Bind(wx.EVT_BUTTON, self.on_edit, self.edit_btn)
        self.Bind(wx.EVT_BUTTON, self.on_delete, self.delete_btn)
        self.Bind(wx.EVT_BUTTON, self.on_refresh, self.refresh_btn)
        self.Bind(wx.EVT_BUTTON, lambda e: self.Close(), close_btn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_task_selected, self.schedule_list)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_task_deselected, self.schedule_list)
        
        # 初始禁用编辑和删除按钮
        self.edit_btn.Disable()
        self.delete_btn.Disable()
    
    def on_task_selected(self, event):
        """选中任务时启用编辑和删除按钮"""
        self.edit_btn.Enable()
        self.delete_btn.Enable()
    
    def on_task_deselected(self, event):
        """取消选中任务时禁用编辑和删除按钮"""
        self.edit_btn.Disable()
        self.delete_btn.Disable()
    
    def refresh_task_list_in_background(self):
        """在后台线程中获取定时任务数据，包括调度器状态"""
        print("refresh_task_list_in_background 开始执行")
        
        # 初始化默认值
        tasks = []
        scheduler_status = {}
        
        try:
            # 1. 从数据库获取所有定时任务
            print("开始查询数据库获取定时任务")
            tasks = self.db_manager.get_all_cron_tasks()
            print(f"数据库查询完成，获取到 {len(tasks)} 个任务")
            
            # 2. 获取调度器中的实际任务状态（如果调度器已初始化）
            if self.scheduler_manager:
                print("开始获取调度器中的任务状态")
                all_status = self.scheduler_manager.get_all_job_status()
                for status in all_status:
                    scheduler_status[status['task_name']] = status
                print(f"从调度器获取到 {len(all_status)} 个任务状态")
            else:
                print("调度器未初始化，跳过获取调度器状态")
        except Exception as e:
            print(f"refresh_task_list_in_background 执行出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 3. 无论如何都要更新UI，确保不会卡在"正在加载"状态
            print(f"最终更新UI，任务数: {len(tasks)}, 调度器状态数: {len(scheduler_status)}")
            wx.CallAfter(self.refresh_task_list, tasks, scheduler_status)
            print("refresh_task_list_in_background 执行完成")
    
    def refresh_task_list(self, tasks=None, scheduler_status=None):
        """刷新定时任务列表（在主线程中执行）"""
        if tasks is None:
            # 如果没有提供任务数据，在后台线程中获取
            threading.Thread(target=self.refresh_task_list_in_background, daemon=True).start()
            return
        
        # 清空列表
        self.schedule_list.DeleteAllItems()
        
        # 填充数据
        print(f"开始刷新任务列表，共 {len(tasks)} 个任务")
        if not tasks:
            # 如果没有任务，显示提示信息
            self.schedule_list.InsertItem(0, "暂无定时任务")
            self.schedule_list.SetItem(0, 1, "")
            self.schedule_list.SetItem(0, 2, "")
            self.schedule_list.SetItem(0, 3, "")
            self.schedule_list.SetItem(0, 4, "")
            self.schedule_list.SetItem(0, 5, "")
        else:
            for i, task in enumerate(tasks):
                # 确保正确解析所有字段
                try:
                    task_name = task[0]
                    cron_expr = task[1]
                    enabled = task[2]
                    params_str = str(task[3]) if len(task) > 3 and task[3] is not None else ""
                    last_run = task[4] if len(task) > 4 else None
                    next_run = task[5] if len(task) > 5 else None
                    
                    # 优先使用调度器中的实际状态
                    actual_status = scheduler_status.get(task_name) if scheduler_status else None
                    if actual_status:
                        # 更新状态和下次运行时间
                        status = "启用" if actual_status['enabled'] else "禁用"
                        next_run = actual_status['next_run']
                    else:
                        # 如果调度器中没有该任务，使用数据库中的状态
                        status = "启用" if enabled else "禁用"
                    
                    # 添加行
                    self.schedule_list.InsertItem(i, task_name)
                    self.schedule_list.SetItem(i, 1, cron_expr)
                    self.schedule_list.SetItem(i, 2, status)
                    self.schedule_list.SetItem(i, 3, params_str)
                    self.schedule_list.SetItem(i, 4, last_run or "从未")
                    self.schedule_list.SetItem(i, 5, next_run or "未知")
                except Exception as e:
                    print(f"解析定时任务数据失败: {task}, 错误: {e}")
    
    def on_add(self, event):
        """添加新的定时任务"""
        # 获取所有可用的爬虫任务
        crawlers = self.crawler_manager.get_crawlers()
        if not crawlers:
            wx.MessageBox("没有可用的爬虫任务", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        
        # 选择任务对话框
        task_names = list(crawlers.keys())
        dlg = wx.SingleChoiceDialog(self, "选择要添加定时的任务", "选择任务", task_names)
        if dlg.ShowModal() == wx.ID_OK:
            selected_task = dlg.GetStringSelection()
            dlg.Destroy()
            
            # 显示设置对话框
            schedule_dlg = ScheduleDialog(self, selected_task, self.scheduler_manager, self.db_manager)
            if schedule_dlg.ShowModal() == wx.ID_OK:
                # 刷新任务列表
                self.refresh_task_list_in_background()
                # 刷新调度器，确保新添加的任务被正确加载
                threading.Thread(target=self.refresh_scheduler, daemon=True).start()
            schedule_dlg.Destroy()
        else:
            dlg.Destroy()
    
    def on_edit(self, event):
        """编辑选中的定时任务"""
        selected = self.schedule_list.GetFirstSelected()
        if selected != -1:
            task_name = self.schedule_list.GetItem(selected, 0).GetText()
            
            # 显示设置对话框
            schedule_dlg = ScheduleDialog(self, task_name, self.scheduler_manager, self.db_manager)
            if schedule_dlg.ShowModal() == wx.ID_OK:
                # 刷新任务列表
                self.refresh_task_list_in_background()
                # 刷新调度器，确保修改后的任务被正确加载
                threading.Thread(target=self.refresh_scheduler, daemon=True).start()
            schedule_dlg.Destroy()
    
    def on_delete(self, event):
        """删除选中的定时任务"""
        selected = self.schedule_list.GetFirstSelected()
        if selected != -1:
            task_name = self.schedule_list.GetItem(selected, 0).GetText()
            
            if wx.MessageBox(f"确定要删除 {task_name} 的定时任务吗？", "确认", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
                # 在后台线程中执行删除操作
                def delete_in_background():
                    try:
                        # 从调度器中移除任务（如果已初始化）
                        if self.scheduler_manager:
                            self.scheduler_manager.remove_job(task_name)
                        # 从数据库中删除任务
                        self.db_manager.delete_cron_task(task_name)
                        # 刷新任务列表
                        wx.CallAfter(self.refresh_task_list_in_background)
                        # 刷新调度器，确保删除的任务被正确移除
                        threading.Thread(target=self.refresh_scheduler, daemon=True).start()
                        # 显示成功提示
                        wx.CallAfter(wx.MessageBox, "定时任务已删除", "提示", wx.OK | wx.ICON_INFORMATION)
                    except Exception as e:
                        print(f"删除定时任务失败: {e}")
                        wx.CallAfter(wx.MessageBox, f"删除失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
                
                # 启动后台线程执行删除操作
                threading.Thread(target=delete_in_background, daemon=True).start()
    
    def on_refresh(self, event):
        """刷新定时任务列表和调度器状态"""
        # 在后台线程中执行刷新操作，避免阻塞UI
        threading.Thread(target=self.refresh_task_list_in_background, daemon=True).start()
    
    def refresh_scheduler(self):
        """在后台线程中刷新调度器"""
        try:
            if self.scheduler_manager:
                # 直接重新加载任务，无需重启调度器
                print("重新加载调度器中的任务")
                self.scheduler_manager.load_tasks()
                # 刷新任务列表
                wx.CallAfter(self.refresh_task_list_in_background)
        except Exception as e:
            print(f"刷新调度器失败: {e}")
            import traceback
            traceback.print_exc()
            wx.CallAfter(wx.MessageBox, f"刷新定时任务失败：{e}", "错误", wx.OK | wx.ICON_ERROR)

class ScheduleDialog(wx.Dialog):
    """定时任务设置对话框"""
    def __init__(self, parent, task_name, scheduler_manager, db_manager):
        super().__init__(parent, title=f"定时设置 - {task_name}", size=(400, 300))
        self.task_name = task_name
        self.scheduler_manager = scheduler_manager
        self.db_manager = db_manager
        
        # 初始化UI，但不加载数据
        self.init_ui_structure()
        
        # 在后台线程中加载数据
        threading.Thread(target=self.load_data_in_background, daemon=True).start()
    
    def init_ui_structure(self):
        """初始化UI结构，但不加载数据"""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 任务名称显示
        self.task_label = wx.StaticText(panel, label=f"任务名称: {self.task_name}")
        self.task_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.task_label, 0, wx.EXPAND | wx.ALL, 5)
        
        # Cron表达式设置
        cron_box = wx.StaticBox(panel, label="Cron表达式")
        cron_box_sizer = wx.StaticBoxSizer(cron_box, wx.VERTICAL)
        
        cron_label = wx.StaticText(panel, label="表达式格式: 分 时 日 月 周 (例如: 0 0 * * * 表示每天凌晨执行)")
        cron_box_sizer.Add(cron_label, 0, wx.EXPAND | wx.ALL, 5)
        
        # 初始化空的文本控件
        self.cron_text = wx.TextCtrl(panel, value="", size=(300, 30))
        cron_box_sizer.Add(self.cron_text, 0, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(cron_box_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # 启用复选框
        self.enable_checkbox = wx.CheckBox(panel, label="启用定时任务")
        sizer.Add(self.enable_checkbox, 0, wx.EXPAND | wx.ALL, 5)
        
        # 参数设置
        param_box = wx.StaticBox(panel, label="定时任务参数")
        param_box_sizer = wx.StaticBoxSizer(param_box, wx.VERTICAL)
        
        param_label = wx.StaticText(panel, label="参数格式: key1=value1,key2=value2")
        param_box_sizer.Add(param_label, 0, wx.EXPAND | wx.ALL, 5)
        
        self.param_text = wx.TextCtrl(panel, value="", style=wx.TE_MULTILINE, size=(300, 80))
        param_box_sizer.Add(self.param_text, 0, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(param_box_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # 按钮
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.save_btn = wx.Button(panel, label="保存")
        self.delete_btn = wx.Button(panel, label="删除定时任务")
        self.cancel_btn = wx.Button(panel, label="取消")
        
        btn_sizer.Add(self.save_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.delete_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.cancel_btn, 0, wx.ALL, 5)
        
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        panel.SetSizer(sizer)
        
        # 绑定事件
        self.Bind(wx.EVT_BUTTON, self.on_save, self.save_btn)
        self.Bind(wx.EVT_BUTTON, self.on_delete, self.delete_btn)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, self.cancel_btn)
        self.Bind(wx.EVT_CLOSE, self.on_close)
    
    def load_data_in_background(self):
        """在后台线程中加载定时任务数据"""
        try:
            # 从数据库获取当前设置
            cron_task = self.db_manager.get_cron_task(self.task_name)
            cron_expression = cron_task[1] if cron_task else ""
            enabled = cron_task[2] if cron_task else 0
            params_str = cron_task[3] if cron_task else ""
            
            # 将数据库中的参数格式转换为用户输入格式（key1=value1,key2=value2）
            params = ""
            if params_str:
                try:
                    import ast
                    params_dict = ast.literal_eval(params_str)
                    if isinstance(params_dict, dict):
                        params = ",".join([f"{k}={v}" for k, v in params_dict.items()])
                except:
                    pass
            
            # 使用wx.CallAfter更新UI
            wx.CallAfter(self.update_ui_with_data, cron_expression, enabled, params)
        except Exception as e:
            print(f"加载定时任务数据失败: {e}")
            wx.CallAfter(wx.MessageBox, f"加载数据失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
    
    def update_ui_with_data(self, cron_expression, enabled, params):
        """更新UI显示数据"""
        self.cron_text.SetValue(cron_expression)
        self.enable_checkbox.SetValue(bool(enabled))
        self.param_text.SetValue(params)
    
    def on_save(self, event):
        """保存定时任务设置"""
        cron_expression = self.cron_text.GetValue().strip()
        enabled = self.enable_checkbox.GetValue()
        params_text = self.param_text.GetValue().strip()
        
        if not cron_expression:
            wx.MessageBox("请输入Cron表达式", "错误", wx.OK | wx.ICON_ERROR)
            return
        
        # 解析参数
        params = {}
        if params_text:
            try:
                # 检查是否为直接的命令行参数字符串，如"--env ly --debug"
                if params_text.strip().startswith("--"):
                    # 直接作为__args__参数
                    params["__args__"] = params_text.strip()
                else:
                    # 尝试解析为字典
                    import ast
                    try:
                        params = ast.literal_eval(params_text)
                        if not isinstance(params, dict):
                            params = {}
                    except:
                        # 解析为key=value格式
                        for param in params_text.split(","):
                            if "=" in param:
                                key, value = param.split("=", 1)
                                params[key.strip()] = value.strip()
                            else:
                                # 单个值，如--verbose
                                key = param.strip()
                                if key.startswith("--"):
                                    params[key] = ""
                                else:
                                    params[key] = ""
            except:
                wx.MessageBox("参数格式错误，支持格式：\n1. key1=value1,key2=value2\n2. --env ly --debug\n3. {\"key\": \"value\"}", "错误", wx.OK | wx.ICON_ERROR)
                return
        
        # 在后台线程中执行保存操作，避免阻塞UI
        def save_in_background():
            try:
                # 保存到数据库
                self.db_manager.add_or_update_cron_task(self.task_name, cron_expression, int(enabled), params)
                
                # 更新调度器（如果已初始化）
                if self.scheduler_manager:
                    self.scheduler_manager.add_job(self.task_name, cron_expression, enabled, params)
                    print(f"调度器中添加任务：{self.task_name}，表达式：{cron_expression}，状态：{'启用' if enabled else '禁用'}")
                
                # 保存完成后关闭对话框
                wx.CallAfter(self.EndModal, wx.ID_OK)
            except Exception as e:
                print(f"保存定时任务失败: {e}")
                wx.CallAfter(wx.MessageBox, f"保存失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
        
        # 启动后台线程执行保存操作
        threading.Thread(target=save_in_background, daemon=True).start()
    
    def on_delete(self, event):
        """删除定时任务"""
        if wx.MessageBox(f"确定要删除 {self.task_name} 的定时任务吗？", "确认", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            # 在后台线程中执行删除操作，避免阻塞UI
            def delete_in_background():
                try:
                    # 从调度器中移除任务（如果已初始化）
                    if self.scheduler_manager:
                        self.scheduler_manager.remove_job(self.task_name)
                    # 从数据库中删除任务
                    self.db_manager.delete_cron_task(self.task_name)
                    # 删除完成后关闭对话框
                    wx.CallAfter(self.EndModal, wx.ID_OK)
                except Exception as e:
                    print(f"删除定时任务失败: {e}")
                    wx.CallAfter(wx.MessageBox, f"删除失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
            
            # 启动后台线程执行删除操作
            threading.Thread(target=delete_in_background, daemon=True).start()
    
    def on_cancel(self, event):
        """取消操作"""
        self.EndModal(wx.ID_CANCEL)
    
    def on_close(self, event):
        """关闭对话框时的处理"""
        # 获取当前设置
        current_cron_expression = self.cron_text.GetValue().strip()
        current_enabled = self.enable_checkbox.GetValue()
        current_params_text = self.param_text.GetValue().strip()
        
        # 在后台线程中检查是否有未保存的更改
        threading.Thread(
            target=self.check_changes_in_background,
            args=(current_cron_expression, current_enabled, current_params_text, event),
            daemon=True
        ).start()
    
    def check_changes_in_background(self, current_cron_expression, current_enabled, current_params_text, event):
        """在后台线程中检查是否有未保存的更改"""
        try:
            # 检查是否有未保存的更改
            original_cron_task = self.db_manager.get_cron_task(self.task_name)
            original_cron_expression = original_cron_task[1] if original_cron_task else ""
            original_enabled = original_cron_task[2] if original_cron_task else 0
            original_params_str = original_cron_task[3] if original_cron_task else ""
            
            # 比较当前设置与原始设置
            changes_made = False
            if current_cron_expression != original_cron_expression:
                changes_made = True
            elif current_enabled != bool(original_enabled):
                changes_made = True
            else:
                # 比较参数
                original_params = ""
                if original_params_str:
                    try:
                        import ast
                        original_params_dict = ast.literal_eval(original_params_str)
                        if isinstance(original_params_dict, dict):
                            original_params = ",".join([f"{k}={v}" for k, v in original_params_dict.items()])
                    except:
                        pass
                if current_params_text != original_params:
                    changes_made = True
            
            if changes_made:
                # 在主线程中显示对话框
                wx.CallAfter(self.prompt_save_changes)
            else:
                # 没有更改，直接关闭
                wx.CallAfter(self.EndModal, wx.ID_CANCEL)
        except Exception as e:
            print(f"检查更改失败: {e}")
            # 出错时直接关闭
            wx.CallAfter(self.EndModal, wx.ID_CANCEL)
    
    def prompt_save_changes(self):
        """在主线程中提示用户是否保存更改"""
        result = wx.MessageBox("您有未保存的更改，是否保存？", "提示", wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
        if result == wx.YES:
            # 保存更改
            self.on_save(None)
        elif result == wx.CANCEL:
            return  # 取消关闭
        # 如果是wx.NO或者保存成功，则直接关闭
        self.EndModal(wx.ID_CANCEL)

if __name__ == "__main__":
    print("初始化wxApp...")
    app = wx.App()
    
    print("创建CrawlerGUI实例...")
    frame = CrawlerGUI()
    
    print("显示界面...")
    frame.Show()
    frame.Raise()  # 确保窗口在最前面
    
    print("启动主循环...")
    app.MainLoop()
