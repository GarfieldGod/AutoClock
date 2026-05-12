import subprocess
import re
import threading
import time

from src.utils.log import Log

def disconnect_network(delay_seconds=0):
    """
    断开网络连接
    
    :param delay_seconds: 延迟执行的秒数，默认为0（立即执行）
    :return: (是否成功, 错误信息)
    """
    if delay_seconds > 0:
        try:
            # 创建并启动线程来延迟执行断网操作
            disconnect_thread = threading.Thread(
                target=_disconnect_network_after_delay,
                args=(delay_seconds,),
                daemon=False
            )
            disconnect_thread.start()
            return True, None
        except Exception as e:
            Log.error(f"启动断网延迟任务时出错: {str(e)}")
            return False, str(e)
    else:
        # 立即执行断网操作
        return _disconnect_network_impl()

def _disconnect_network_after_delay(delay_seconds):
    """
    延迟执行断网操作的后台函数
    
    :param delay_seconds: 延迟的秒数
    """
    Log.info(f"后台断网任务已启动，将在 {delay_seconds} 秒后执行")
    time.sleep(delay_seconds)
    _disconnect_network_impl()

def _disconnect_network_impl():
    """
    断开网络连接的实现函数
    """
    try:
        # 使用更可靠的命令获取网络接口
        result = subprocess.run(["netsh", "interface", "show", "interface"], 
                                capture_output=True, text=True, shell=True, encoding='gbk')
        if result.returncode != 0:
            return False, f"获取网络接口失败: {result.stderr}"
        
        disabled_interfaces = []
        
        # 使用更健壮的解析方式
        stdout_text = (result.stdout or "")
        lines = stdout_text.strip().split('\n') if stdout_text else []
        
        for line in lines:
            line = line.strip()
            # 匹配已启用的接口行
            if re.search(r'Enabled\s+(\w+\s+)+', line) or re.search(r'已启用\s+(\w+\s+)+', line):
                # 提取接口名称 - 更灵活的方式
                parts = line.split()
                if len(parts) >= 4:
                    # 接口名称通常在最后，可能包含空格
                    interface_name = ' '.join(parts[3:]).strip()
                    if interface_name and interface_name not in disabled_interfaces:
                        # 禁用接口
                        disable_result = subprocess.run([
                            "netsh", "interface", "set", "interface", 
                            f"name={interface_name}", "admin=disable"
                        ], capture_output=True, text=True, shell=True, encoding='gbk')
                        
                        if disable_result.returncode == 0:
                            disabled_interfaces.append(interface_name)
                            Log.info(f"成功禁用接口: {interface_name}")
                        else:
                            Log.warning(f"禁用接口 {interface_name} 失败: {disable_result.stderr}")
        
        # 特别处理WiFi - 使用专门的WiFi命令
        try:
            wifi_result = subprocess.run([
                "netsh", "wlan", "disconnect"
            ], capture_output=True, text=True, shell=True, encoding='gbk')
            
            if wifi_result.returncode == 0:
                Log.info("WiFi断开成功")
            else:
                Log.info("WiFi断开命令执行")
        except Exception as e:
            Log.warning(f"WiFi断开命令执行异常: {str(e)}")
        
        if disabled_interfaces:
            Log.info(f"网络断开成功，禁用了 {len(disabled_interfaces)} 个接口")
            return True, None
        else:
            # 如果没有找到需要禁用的接口，检查是否所有接口都已禁用（即网络已断开）
            all_disabled = True
            for line in lines:
                line = line.strip()
                if re.search(r'Enabled\s+(\w+\s+)+', line) or re.search(r'已启用\s+(\w+\s+)+', line):
                    all_disabled = False
                    break
            
            if all_disabled:
                Log.info("网络已处于断开状态，无需操作")
                return True, None
            else:
                Log.warning("未找到需要禁用的网络接口")
                return False, "未找到需要禁用的网络接口"
            
    except Exception as e:
        Log.error(f"断开网络时出错: {str(e)}")
        return False, str(e)

def connect_network(delay_seconds=0):
    """
    连接网络 - 改进版
    
    :param delay_seconds: 延迟执行的秒数，默认为0（立即执行）
    :return: (是否成功, 错误信息)
    """
    if delay_seconds > 0:
        try:
            # 创建并启动线程来延迟执行连接网络操作
            connect_thread = threading.Thread(
                target=connect_network_after_delay,
                args=(delay_seconds,),
                daemon=False
            )
            connect_thread.start()
            return True, None
        except Exception as e:
            Log.error(f"启动网络连接延迟任务时出错: {str(e)}")
            return False, str(e)
    else:
        # 立即执行连接网络操作
        return _connect_network_impl()

def connect_network_after_delay(delay_seconds):
    """
    延迟执行连接网络操作的后台函数
    
    :param delay_seconds: 延迟的秒数
    """
    Log.info(f"后台网络连接任务已启动，将在 {delay_seconds} 秒后执行")
    time.sleep(delay_seconds)
    _connect_network_impl()

def _connect_network_impl():
    """
    连接网络的实现函数
    """
    try:
        result = subprocess.run(["netsh", "interface", "show", "interface"], 
                                capture_output=True, text=True, shell=True, encoding='gbk')
        if result.returncode != 0:
            return False, f"获取网络接口失败: {result.stderr}"
        
        enabled_interfaces = []
        
        stdout_text = (result.stdout or "")
        lines = stdout_text.strip().split('\n') if stdout_text else []
        
        for line in lines:
            line = line.strip()
            # 匹配已禁用的接口行
            if re.search(r'Disabled\s+(\w+\s+)+', line) or re.search(r'已禁用\s+(\w+\s+)+', line):
                parts = line.split()
                if len(parts) >= 4:
                    interface_name = ' '.join(parts[3:]).strip()
                    if interface_name and interface_name not in enabled_interfaces:
                        # 启用接口
                        enable_result = subprocess.run([
                            "netsh", "interface", "set", "interface", 
                            f"name={interface_name}", "admin=enable"
                        ], capture_output=True, text=True, shell=True, encoding='gbk')
                        
                        if enable_result.returncode == 0:
                            enabled_interfaces.append(interface_name)
                            Log.info(f"成功启用接口: {interface_name}")
                        else:
                            Log.warning(f"启用接口 {interface_name} 失败: {enable_result.stderr}")
        
        # 尝试重新连接WiFi
        try:
            wifi_result = subprocess.run([
                "netsh", "wlan", "connect", "name=*"
            ], capture_output=True, text=True, shell=True, encoding='gbk')
            
            if wifi_result.returncode == 0:
                Log.info("WiFi重新连接命令执行成功")
        except Exception as e:
            Log.warning(f"WiFi连接命令执行异常: {str(e)}")
        
        if enabled_interfaces:
            Log.info(f"网络连接成功，启用了 {len(enabled_interfaces)} 个接口")
            return True, None
        else:
            # 如果没有找到需要启用的接口，检查是否所有接口都已启用（即网络已连接）
            all_enabled = True
            for line in lines:
                line = line.strip()
                if re.search(r'Disabled\s+(\w+\s+)+', line) or re.search(r'已禁用\s+(\w+\s+)+', line):
                    all_enabled = False
                    break
            
            if all_enabled:
                Log.info("网络已处于连接状态，无需操作")
                return True, None
            else:
                Log.warning("未找到需要启用的网络接口")
                return False, "未找到需要启用的网络接口"
            
    except Exception as e:
        Log.error(f"连接网络时出错: {str(e)}")
        return False, str(e)

# 可选：专门针对WiFi的函数
def toggle_wifi(enable=True):
    """
    专门控制WiFi开关
    """
    try:
        if enable:
            result = subprocess.run([
                "netsh", "interface", "set", "interface", "Wi-Fi", "admin=enable"
            ], capture_output=True, text=True, shell=True, encoding='gbk')
            action = "启用"
        else:
            result = subprocess.run([
                "netsh", "interface", "set", "interface", "Wi-Fi", "admin=disable"
            ], capture_output=True, text=True, shell=True, encoding='gbk')
            action = "禁用"
        
        if result.returncode == 0:
            Log.info(f"WiFi{action}成功")
            return True, None
        else:
            Log.error(f"WiFi{action}失败: {result.stderr}")
            return False, result.stderr
            
    except Exception as e:
        Log.error(f"控制WiFi时出错: {str(e)}")
        return False, str(e)