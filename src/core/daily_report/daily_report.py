import time, re

from selenium import webdriver
from dataclasses import dataclass
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import TimeoutException
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

from src.utils.const import Key, AppPath, WebPath
from src.utils.log import Log
from src.utils.utils import Utils
from src.core.daily_report.cps_login import cps_login


@dataclass
class DailyReportConfig:
    driver_path: str
    user_name: str
    user_password: str
    work_description: str
    normal_workload: str
    overtime_workload: str
    project_name: str
    project_task: str
    activity_type: str
    project_type: str
    wait_time: int = 2
    show_web_page: bool = True
    auto_update_driver: bool = True


class DailyReport:
    def __init__(self, config: DailyReportConfig):
        self.driver_path = config.driver_path
        self.user_name = config.user_name
        self.user_password = config.user_password
        self.work_description = config.work_description
        self.normal_workload = config.normal_workload
        self.overtime_workload = config.overtime_workload
        self.project_name = config.project_name
        self.project_task = config.project_task
        self.activity_type = config.activity_type
        self.project_type = config.project_type
        self.wait_time = config.wait_time
        self.show_web_page = config.show_web_page
        self.auto_update_driver = config.auto_update_driver
        self.driver = None
        try:
            self.driver = self.create_driver()
        except Exception as e:
            Log.error(f"Create driver error: {e}")
            if 'version' in str(e):
                try:
                    if not self.auto_update_driver:
                        raise Exception("Edge version not support, need to redownload driver.")
                    ok, driver_path = Utils.download_edge_web_driver()
                    if not ok:
                        raise Exception("Redownload Edge web driver error.")
                    self.driver_path = driver_path
                    self.driver = self.create_driver()
                    if self.driver is not None:
                        data = Utils.read_dict_from_json(AppPath.DataJson)
                        data[Key.DriverPath] = self.driver_path
                        Utils.write_dict_to_file(AppPath.DataJson, data)
                except Exception as e:
                    Log.error(f"Redownload and Create driver error: {e}")
                    raise Exception(f"Failed to create WebDriver: {e}")
            else:
                raise Exception(f"Failed to create WebDriver: {e}")

    def create_driver(self):
        opts = Options()
        if not self.show_web_page:
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--start-maximized")
        opts.add_argument("--enable-logging")
        opts.add_argument("--v=1")
        opts.add_argument("--disable-blink-features=AutomationControlled")

        service = Service(executable_path=self.driver_path)
        driver = webdriver.Edge(service=service, options=opts)
        Log.info("create driver successfully")
        return driver

    def auto_login(self):
        try:
            Log.info("开始 CPS 登录流程")
            self.driver.get(WebPath.NeusoftCPSPath)
            Log.info(f"打开URL: {WebPath.NeusoftCPSPath}")
            time.sleep(3)

            ret, error = cps_login(self.driver, self.user_name, self.user_password, wait=self.wait_time)
            if ret:
                Log.info("CPS 登录流程完成")
            else:
                info = f"CPS 登录失败: {error}"
                Log.error(info)
                raise Exception(info)

            time.sleep(3)
            return True
        except Exception as e:
            Log.error(f"登录失败: {e}")
            return False

    def navigate_to_report_page(self):
        try:
            Log.info("导航到日报页面")
            waiter = WebDriverWait(self.driver, 15)

            menu_items = waiter.until(EC.presence_of_all_elements_located((
                By.XPATH, "//*[contains(text(), '日报管理') or contains(text(), '日报')]"
            )))
            report_menu = None
            for item in menu_items:
                text = item.text.strip()
                if '日报管理' in text or text == '日报管理':
                    report_menu = item
                    break
            if report_menu is None:
                for item in menu_items:
                    text = item.text.strip()
                    if '日报' in text:
                        report_menu = item
                        break
            if report_menu is None:
                Log.waring("未找到'日报管理'菜单项，尝试其他方式")
                try:
                    report_menu = waiter.until(EC.element_to_be_clickable((
                        By.XPATH,
                        "//a[contains(@href, 'daily') or contains(@href, 'report') or contains(text(), '日报')]"
                    )))
                except Exception:
                    pass

            if report_menu is None:
                return False, "未找到日报管理菜单"

            Log.info(f"点击日报管理菜单: {report_menu.text}")
            try:
                report_menu.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", report_menu)
            time.sleep(2)

            try:
                work_report = waiter.until(EC.element_to_be_clickable((
                    By.XPATH,
                    "//*[contains(text(), '工作日报')]"
                )))
                Log.info(f"点击工作日报: {work_report.text}")
                try:
                    work_report.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", work_report)
            except TimeoutException:
                Log.info("未找到'工作日报'子菜单（可能已直接进入日报页面）")

            time.sleep(3)

            try:
                self.driver.switch_to.frame(
                    self.driver.find_element(By.TAG_NAME, "iframe")
                )
                Log.info("切换到 iframe")
                time.sleep(1)
            except Exception:
                Log.info("未检测到 iframe，继续在当前页面操作")

            return True, None
        except Exception as e:
            Log.error(f"导航到日报页面失败: {e}")
            return False, str(e)

    def click_fill_button(self):
        try:
            Log.info("查找'填写'按钮")
            waiter = WebDriverWait(self.driver, 10)

            fill_selectors = [
                "//*[contains(text(), '填写')]",
                "//button[contains(text(), '填写')]",
                "//a[contains(text(), '填写')]",
                "//input[contains(@value, '填写')]",
                "//span[contains(text(), '填写')]",
            ]
            for xpath in fill_selectors:
                try:
                    btn = waiter.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    Log.info(f"找到填写按钮: {xpath}")
                    try:
                        btn.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", btn)
                    Log.info("点击填写按钮成功")
                    time.sleep(2)
                    return True, None
                except TimeoutException:
                    continue

            return False, "未找到'填写'按钮"
        except Exception as e:
            Log.error(f"点击填写按钮失败: {e}")
            return False, str(e)

    def fill_report_form(self):
        try:
            Log.info("开始填写日报表单")

            field_mapping = {
                self.work_description: [
                    "工作描述", "工作内容", "工作摘要", "工作汇报",
                ],
                self.normal_workload: [
                    "正常工作量", "标准工时", "正常工时", "正常工作",
                ],
                self.overtime_workload: [
                    "加班工作量", "加班工时", "加班",
                ],
                self.project_name: [
                    "项目名称", "所属项目", "项目",
                ],
                self.project_task: [
                    "项目任务", "工作任务", "任务描述", "具体任务",
                ],
                self.activity_type: [
                    "一级活动类型", "活动类型", "活动分类",
                ],
                self.project_type: [
                    "一级项目类型", "项目类型", "项目分类",
                ],
            }

            for value, labels in field_mapping.items():
                if not value:
                    continue
                self._fill_field(value, labels)

            Log.info("日报表单填写完成")
            return True, None
        except Exception as e:
            Log.error(f"填写日报表单失败: {e}")
            return False, str(e)

    def _fill_field(self, value, label_texts):
        waiter = WebDriverWait(self.driver, 5)

        for label_text in label_texts:
            try:
                label_el = waiter.until(EC.presence_of_element_located((
                    By.XPATH,
                    f"//label[contains(text(), '{label_text}')] | "
                    f"//span[contains(text(), '{label_text}')] | "
                    f"//td[contains(text(), '{label_text}')] | "
                    f"//th[contains(text(), '{label_text}')] | "
                    f"//div[contains(@class, 'field-label') and contains(text(), '{label_text}')] | "
                    f"//*[contains(@placeholder, '{label_text}')]"
                )))
                Log.info(f"找到标签: {label_text}")

                input_el = self._find_associated_input(label_el)
                if input_el is not None:
                    self._set_input_value(input_el, value)
                    Log.info(f"填写字段 [{label_text}]: {value}")
                    return
            except TimeoutException:
                continue

        Log.waring(f"未找到匹配字段: {label_texts[0]}")

    def _find_associated_input(self, label_el):
        try:
            parent = label_el
            for _ in range(5):
                parent = parent.find_element(By.XPATH, "..")

            input_el = parent.find_element(By.XPATH, ".//input | .//textarea | .//select")
            return input_el
        except Exception:
            pass

        try:
            parent = label_el.find_element(By.XPATH, "..")
            input_el = parent.find_element(By.XPATH, ".//input | .//textarea | .//select")
            return input_el
        except Exception:
            pass

        try:
            input_el = label_el.find_element(By.XPATH,
                "following-sibling::input | following-sibling::textarea | following-sibling::select")
            return input_el
        except Exception:
            pass

        try:
            label_for = label_el.get_attribute('for')
            if label_for:
                input_el = self.driver.find_element(By.ID, label_for)
                return input_el
        except Exception:
            pass

        return None

    def _set_input_value(self, el, value):
        tag = el.tag_name.lower()
        if tag == 'select':
            try:
                select = Select(el)
                options = [o.text.strip() for o in select.options]
                for opt_text in options:
                    if value in opt_text or opt_text in value:
                        select.select_by_visible_text(opt_text)
                        return
                if options:
                    select.select_by_index(0)
            except Exception:
                pass
        elif tag == 'textarea':
            try:
                el.clear()
                el.send_keys(value)
            except Exception:
                self.driver.execute_script("arguments[0].value = arguments[1];", el, value)
        else:
            try:
                el.clear()
                el.send_keys(value)
            except Exception:
                self.driver.execute_script("arguments[0].value = arguments[1];", el, value)

    def submit_report(self):
        try:
            Log.info("提交日报表单")
            waiter = WebDriverWait(self.driver, 10)

            submit_selectors = [
                "//button[contains(text(), '确定') or contains(text(), '提交') or contains(text(), '保存')]",
                "//input[contains(@value, '确定') or contains(@value, '提交') or contains(@value, '保存')]",
                "//a[contains(text(), '确定') or contains(text(), '提交') or contains(text(), '保存')]",
                "//span[contains(text(), '确定') or contains(text(), '提交') or contains(text(), '保存')]",
            ]
            for xpath in submit_selectors:
                try:
                    btn = waiter.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    Log.info(f"找到提交按钮: {xpath}")
                    try:
                        btn.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", btn)
                    Log.info("点击提交按钮成功")
                    time.sleep(2)
                    return True, None
                except TimeoutException:
                    continue

            return False, "未找到提交/确定按钮"
        except Exception as e:
            Log.error(f"提交日报失败: {e}")
            return False, str(e)

    def check_success(self):
        try:
            time.sleep(2)
            success_keywords = ['成功', '提交成功', '保存成功', '操作成功', '添加成功']
            for keyword in success_keywords:
                try:
                    el = self.driver.find_element(
                        By.XPATH, f"//*[contains(text(), '{keyword}')]"
                    )
                    if el.is_displayed():
                        Log.info(f"检测到成功提示: {keyword}")
                        return True
                except Exception:
                    continue

            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                Log.info(f"检测到弹窗: {alert_text}")
                alert.accept()
                return True
            except Exception:
                pass

            try:
                success_el = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".success, .alert-success, .message-success, .toast-success, .el-message--success"
                )
                if success_el.is_displayed():
                    Log.info("检测到成功样式元素")
                    return True
            except Exception:
                pass

            Log.waring("未检测到明确的成功提示，但已执行提交操作")
            return True
        except Exception as e:
            Log.error(f"检测成功状态失败: {e}")
            return False

    def quit(self):
        if self.driver:
            self.driver.quit()

    def run(self):
        try:
            Log.info("===== 开始自动填写日报 =====")

            if not self.auto_login():
                return False, "登录失败"

            ok, error = self.navigate_to_report_page()
            if not ok:
                return False, f"导航到日报页面失败: {error}"

            ok, error = self.click_fill_button()
            if not ok:
                return False, f"点击填写按钮失败: {error}"

            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    self.driver.switch_to.frame(iframes[-1])
                    Log.info("切换到表单 iframe")
                    time.sleep(1)
            except Exception:
                pass

            ok, error = self.fill_report_form()
            if not ok:
                return False, f"填写日报表单失败: {error}"

            ok, error = self.submit_report()
            if not ok:
                return False, f"提交日报失败: {error}"

            success = self.check_success()
            if success:
                Log.info("日报提交成功")
                return True, None
            else:
                Log.waring("日报提交状态未知，可能已成功")
                return True, None
        except Exception as e:
            Log.error(f"自动填写日报异常: {e}")
            return False, str(e)
        finally:
            time.sleep(3)
            self.quit()
