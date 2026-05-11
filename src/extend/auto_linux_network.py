import subprocess
import re
import threading
import time
import os

from src.utils.log import Log
from src.utils.const import Key


def _check_command_availability(command):
    """
    检查命令是否可用
    """
    try:
        subprocess.run([command, '--help'], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _get_network_interfaces():
    """
    获取网络接口列表
    """
    interfaces = []
    try:
        # 优先使用ip命令
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            # 解析ip命令输出
            pattern = r'\d+:\s+([^:]+):'
            matches = re.findall(pattern, result.stdout)
            interfaces = [iface.strip() for iface in matches]
        else:
            # 尝试使用ifconfig命令
            result = subprocess.run(['ifconfig', '-a'], capture_output=True, text=True)
            if result.returncode == 0:
                # 解析ifconfig命令输出
                pattern = r'^(\w+):?'
                matches = re.findall(pattern, result.stdout, re.MULTILINE)
                interfaces = [iface.strip() for iface in matches]
    except Exception as e:
        Log.error(f"获取网络接口时出错: {str(e)}")
    
    return interfaces


def _get_interface_status(interface):
    """
    获取网络接口状态
    """
    try:
        result = subprocess.run(['ip', 'link', 'show', interface], capture_output=True, text=True)
        if result.returncode == 0:
            return 'UP' in result.stdout
        return False
    except Exception as e:
        Log.error(f"获取接口状态时出错: {str(e)}")
        return False


def _disable_interface(interface):
    """
    禁用网络接口
    """
    try:
        # 检查是否需要sudo权限
        requires_sudo = False
        test_result = subprocess.run(['ip', 'link', 'set', interface, 'down'], capture_output=True)
        if test_result.returncode != 0:
            requires_sudo = True
        
        # 执行禁用命令
        if requires_sudo:
            result = subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'down'], capture_output=True, text=True)
        else:
            result = subprocess.run(['ip', 'link', 'set', interface, 'down'], capture_output=True, text=True)
        
        if result.returncode == 0:
            Log.info(f"成功禁用接口: {interface}")
            return True
        else:
            Log.warning(f"禁用接口 {interface} 失败: {result.stderr}")
            return False
    except Exception as e:
        Log.error(f"禁用接口时出错: {str(e)}")
        return False


def _enable_interface(interface):
    """
    启用网络接口
    """
    try:
        # 检查是否需要sudo权限
        requires_sudo = False
        test_result = subprocess.run(['ip', 'link', 'set', interface, 'up'], capture_output=True)
        if test_result.returncode != 0:
            requires_sudo = True
        
        # 执行启用命令
        if requires_sudo:
            result = subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'up'], capture_output=True, text=True)
        else:
            result = subprocess.run(['ip', 'link', 'set', interface, 'up'], capture_output=True, text=True)
        
        if result.returncode == 0:
            Log.info(f"成功启用接口: {interface}")
            return True
        else:
            Log.warning(f"启用接口 {interface} 失败: {result.stderr}")
            return False
    except Exception as e:
        Log.error(f"启用接口时出错: {str(e)}")
        return False


def _restart_network_manager():
    """
    重启网络管理器（如果可用）
    """
    try:
        # 尝试使用systemctl重启NetworkManager
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'NetworkManager'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            Log.info("成功重启NetworkManager")
            return True
        
        # 尝试使用systemctl重启networking
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'networking'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            Log.info("成功重启networking服务")
            return True
    except Exception as e:
        Log.warning(f"重启网络管理器时出错: {str(e)}")
    
    return False


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
        # 获取网络接口列表
        interfaces = _get_network_interfaces()
        disabled_interfaces = []
        
        # 跳过本地回环接口
        for interface in interfaces:
            if interface.startswith('lo'):
                continue
                
            # 检查接口状态
            if _get_interface_status(interface):
                # 禁用接口
                if _disable_interface(interface):
                    disabled_interfaces.append(interface)
        
        # 特别处理WiFi（如果使用NetworkManager）
        if _check_command_availability('nmcli'):
            try:
                # 禁用所有WiFi连接
                subprocess.run(['sudo', 'nmcli', 'radio', 'wifi', 'off'], 
                              capture_output=True, text=True)
                Log.info("WiFi已关闭")
            except Exception as e:
                Log.warning(f"关闭WiFi时出错: {str(e)}")
        
        if disabled_interfaces:
            Log.info(f"网络断开成功，禁用了 {len(disabled_interfaces)} 个接口")
            return True, None
        else:
            # 检查是否所有接口都已禁用
            all_disabled = True
            for interface in interfaces:
                if interface.startswith('lo'):
                    continue
                if _get_interface_status(interface):
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
    连接网络
    
    :param delay_seconds: 延迟执行的秒数，默认为0（立即执行）
    :return: (是否成功, 错误信息)
    """
    if delay_seconds > 0:
        try:
            # 创建并启动线程来延迟执行连接网络操作
            connect_thread = threading.Thread(
                target=_connect_network_after_delay,
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


def _connect_network_after_delay(delay_seconds):
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
        # 获取网络接口列表
        interfaces = _get_network_interfaces()
        enabled_interfaces = []
        
        # 跳过本地回环接口
        for interface in interfaces:
            if interface.startswith('lo'):
                continue
                
            # 检查接口状态
            if not _get_interface_status(interface):
                # 启用接口
                if _enable_interface(interface):
                    enabled_interfaces.append(interface)
        
        # 特别处理WiFi（如果使用NetworkManager）
        if _check_command_availability('nmcli'):
            try:
                # 启用WiFi
                subprocess.run(['sudo', 'nmcli', 'radio', 'wifi', 'on'], 
                              capture_output=True, text=True)
                Log.info("WiFi已开启")
                
                # 尝试重新连接到最后一个连接
                result = subprocess.run(['nmcli', '-g', 'NAME', 'connection', 'show', '--active'], 
                                      capture_output=True, text=True)
                active_stdout = (result.stdout or "")
                active_connections = active_stdout.strip().split('\n') if active_stdout else []
                
                if not active_connections or not active_connections[0]:
                    # 尝试重新连接到之前使用的WiFi
                    result = subprocess.run(['nmcli', '-g', 'NAME', 'connection', 'show', '--order', 'timestamp'], 
                                          capture_output=True, text=True)
                    conn_stdout = (result.stdout or "")
                    connections = conn_stdout.strip().split('\n') if conn_stdout else []
                    
                    if connections and connections[0]:
                        subprocess.run(['sudo', 'nmcli', 'connection', 'up', connections[0]], 
                                      capture_output=True, text=True)
                        Log.info(f"尝试重新连接到WiFi: {connections[0]}")
            except Exception as e:
                Log.warning(f"开启WiFi时出错: {str(e)}")
        
        # 重启网络管理器（如果启用了接口）
        if enabled_interfaces:
            _restart_network_manager()
            Log.info(f"网络连接成功，启用了 {len(enabled_interfaces)} 个接口")
            return True, None
        else:
            # 检查是否所有接口都已启用
            all_enabled = True
            for interface in interfaces:
                if interface.startswith('lo'):
                    continue
                if not _get_interface_status(interface):
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


def toggle_wifi(enable=True):
    """
    专门控制WiFi开关
    """
    try:
        # 检查nmcli命令是否可用
        if not _check_command_availability('nmcli'):
            Log.error("nmcli命令不可用，无法控制WiFi")
            return False, "nmcli命令不可用"
        
        action = 'on' if enable else 'off'
        result = subprocess.run(['sudo', 'nmcli', 'radio', 'wifi', action], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            Log.info(f"WiFi已{action}")
            return True, None
        else:
            Log.error(f"设置WiFi状态失败: {result.stderr}")
            return False, result.stderr
            
    except Exception as e:
            Log.error(f"控制WiFi时出错: {str(e)}")
            return False, str(e)


def check_network_status():
    """
    检查网络连接状态
    :return: (是否连接, 详细信息)
    """
    try:
        # 尝试ping一个公共DNS服务器来测试连接
        result = subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            Log.info("网络连接正常")
            return True, "网络连接正常"
        else:
            # 检查是否有活动的网络接口
            interfaces = _get_network_interfaces()
            active_interfaces = []
            for interface in interfaces:
                if interface.startswith('lo'):
                    continue
                if _get_interface_status(interface):
                    active_interfaces.append(interface)
            
            if active_interfaces:
                Log.warning(f"网络接口已启用但无法连接外网，活动接口: {', '.join(active_interfaces)}")
                return False, f"网络接口已启用但无法连接外网: {', '.join(active_interfaces)}"
            else:
                Log.warning("网络接口未启用")
                return False, "网络接口未启用"
    except Exception as e:
        Log.error(f"检查网络状态时出错: {str(e)}")
        return False, str(e)


def get_network_info():
    """
    获取网络信息
    :return: 网络信息字典
    """
    try:
        network_info = {
            "interfaces": [],
            "wifi_enabled": False,
            "status": "disconnected"
        }
        
        # 获取网络接口信息
        interfaces = _get_network_interfaces()
        for interface in interfaces:
            if interface.startswith('lo'):
                continue
                
            interface_info = {
                "name": interface,
                "status": "up" if _get_interface_status(interface) else "down"
            }
            network_info["interfaces"].append(interface_info)
        
        # 检查WiFi状态
        if _check_command_availability('nmcli'):
            result = subprocess.run(['nmcli', 'radio', 'wifi'], 
                                   capture_output=True, text=True)
            if result.returncode == 0 and 'enabled' in result.stdout:
                network_info["wifi_enabled"] = True
        
        # 检查整体连接状态
        is_connected, _ = check_network_status()
        if is_connected:
            network_info["status"] = "connected"
        
        Log.info(f"获取网络信息成功: {network_info}")
        return network_info
    except Exception as e:
        Log.error(f"获取网络信息时出错: {str(e)}")
        return {"error": str(e)}


# 兼容Windows函数名（为了系统集成）
def get_network_manager():
    """
    获取网络管理器实例（为了与Windows版本兼容）
    :return: 当前模块
    """
    Log.info("获取Linux网络管理器")
    return sys.modules[__name__]

import sys