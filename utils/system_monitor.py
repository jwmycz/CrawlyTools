import psutil
import time

class SystemMonitor:
    def __init__(self):
        self.last_cpu_percent = None
        
    def get_cpu_usage(self):
        """
        获取CPU使用率（百分比）
        """
        # 第一次调用返回0.0，第二次调用返回真实值
        cpu_percent = psutil.cpu_percent(interval=0.1)
        return cpu_percent
    
    def get_memory_usage(self):
        """
        获取内存使用情况
        返回：已用内存(MB), 总内存(MB), 使用率(%)
        """
        mem = psutil.virtual_memory()
        used = mem.used / (1024 * 1024)  # 转换为MB
        total = mem.total / (1024 * 1024)  # 转换为MB
        percent = mem.percent
        return used, total, percent
    
    def get_disk_usage(self):
        """
        获取磁盘使用情况
        返回：已用空间(GB), 总空间(GB), 使用率(%)
        """
        disk = psutil.disk_usage('/')
        used = disk.used / (1024 * 1024 * 1024)  # 转换为GB
        total = disk.total / (1024 * 1024 * 1024)  # 转换为GB
        percent = disk.percent
        return used, total, percent
    
    def get_system_info(self):
        """
        获取完整的系统资源信息
        """
        cpu = self.get_cpu_usage()
        mem_used, mem_total, mem_percent = self.get_memory_usage()
        disk_used, disk_total, disk_percent = self.get_disk_usage()
        
        return {
            'cpu': round(cpu, 1),
            'memory': {
                'used': round(mem_used, 1),
                'total': round(mem_total, 1),
                'percent': round(mem_percent, 1)
            },
            'disk': {
                'used': round(disk_used, 1),
                'total': round(disk_total, 1),
                'percent': round(disk_percent, 1)
            },
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_system_info_string(self):
        """
        获取格式化的系统资源信息字符串
        """
        info = self.get_system_info()
        return f"CPU: {info['cpu']}% | 内存: {info['memory']['used']}/{info['memory']['total']}MB ({info['memory']['percent']}%) | 磁盘: {info['disk']['used']}/{info['disk']['total']}GB ({info['disk']['percent']}%)"