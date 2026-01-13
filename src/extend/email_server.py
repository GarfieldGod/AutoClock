import smtplib
from datetime import datetime
from email.header import Header
from email.utils import formataddr
from email.mime.text import MIMEText

from PyQt5.QtCore import QDate

from src.utils.log import Log
from src.utils.const import Key
from src.utils.utils import Utils

def get_email_message(email_subject, content_title, hello_message, content_message, sender_email, receiver_email, success=False):
    Log.info(f"email_subject: {email_subject}")
    Log.info(f"content_title: {content_title}")
    Log.info(f"hello_message: {hello_message}")
    # Log.info(f"content_message: {content_message}")
    Log.info(f"sender_email: {sender_email}")
    Log.info(f"receiver_email: {receiver_email}")
    msg = MIMEText(html_content(f"{content_title}",f"{hello_message}", f"{content_message}", success=success), _subtype="html", _charset="utf-8")
    msg["From"] = formataddr(("Auto Clock", f"{sender_email}"))
    msg["To"] = Header(f"{receiver_email}", "utf-8")
    msg["Subject"] = Header(f"{email_subject}", "utf-8")
    return msg

def send_email(context):
    if context.get("smtp_server") is None or context.get("smtp_port") is None or context.get(
            "sender_email") is None or context.get("sender_auth_code") is None or context.get(
            "receiver_email") is None or context.get("message") is None or context.get(
            "subject") is None or context.get("title") is None or context.get("hello") is None:
        message = "Empty context!"
        return False, message
    try:
        message = get_email_message(context.get("subject"), context.get("title"),context.get("hello"),context.get("message"),
                                    context.get("sender_email"), context.get("receiver_email"), context.get("success", False))

        server = smtplib.SMTP_SSL(context.get("smtp_server"), context.get("smtp_port"))
        server.login(context.get("sender_email"), context.get("sender_auth_code"))
        server.sendmail(context.get("sender_email"), context.get("receiver_email"), message.as_string())
        Log.info("HTML Email Send Success!")
        server.quit()
        return True, None
    except Exception as e:
        Log.error(f"HTML Email Send Failed: {str(e)}")
        return False, str(e)

def send_email_by_auto_clock(receiver_email, subject, title, hello, message, ok):
    email_info = {
        "smtp_server": "smtp.163.com",
        "smtp_port": 465,
        "sender_email": "auto_clock@163.com",
        "sender_auth_code": "AXx9tT5cHZKUQXjS",
        "receiver_email": f"{receiver_email}",
        "subject": f"{subject}",
        "title": f"{title}",
        "hello": f"{hello}",
        "message": f"{message}",
        "success": ok
    }
    ret, error = send_email(email_info)
    return ret, error

def send_email_by_result(task, email, send_email_success, send_email_failed, ok, error):
    if not task or not email: return
    if not send_email_success and not send_email_failed: return

    if ok and send_email_success:
        subject = "SUCCESS"
        title = f"SUCCESS:&nbsp;&nbsp;[ {task.get(Key.TaskName, Key.Unknown)} ]"
        hello = f"Your operation [{task.get(Key.Operation, Key.Unknown)}] has completed successfully."
    elif not ok and send_email_failed:
        subject = "FAILED"
        title = f"FAILED:&nbsp;&nbsp;[ {task.get(Key.TaskName, Key.Unknown)} ]"
        hello = f"Sorry, Operation [{task.get(Key.Operation, Key.Unknown)}] Failed.<br>Error Message: {error}"
    else:
        return
    device = Utils.get_device_info()
    device_info = f"{device.get('device_name')} ({device.get('system')} {device.get('version')})" if device else "Unknown Device"
    Log.info(f"device_info: {device_info}")
    ip = Utils.get_location_into()
    ip_info = f"{ip.get('city')} ({ip.get('country')} {ip.get('region')}) {ip.get('ip')}" if ip else "Unknown Location"
    Log.info(f"ip_info: {ip_info}")

    message = get_info_html(task, device_info, ip_info)
    send_email_by_auto_clock(receiver_email=email, subject=subject, title=title, hello=hello, message=message, ok=ok)

def html_content(content_title, hello, message, success):
    content = f"""
    <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: "Microsoft YaHei", Arial, sans-serif;
          }}
          body {{
            background-color: #f5f7fa;
            padding: 20px 0;
          }}
          .email-card {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            overflow: hidden;
          }}
          .card-header {{
            background-color: { "red" if not success else "#4299e1"};
            color: #ffffff;
            padding: 16px 24px;
            font-size: 18px;
            font-weight: 600;
          }}
          .card-content {{
            padding: 24px;
            line-height: 1.8;
            color: #4a5568;
          }}
          .message-content {{
            margin: 16px 0;
            padding: 16px;
            background-color: #f8f9fa;
            border-left: 4px solid { "red" if not success else "#4299e1"};
            border-radius: 4px;
          }}
          .send-time {{
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid #e8f4f8;
            color: #94a3b8;
            font-size: 14px;
            text-align: right;
          }}
          .footer-note {{
            padding: 16px 24px;
            background-color: #f8f9fa;
            color: #94a3b8;
            font-size: 12px;
            text-align: center;
            border-top: 1px solid #e8f4f8;
          }}
        </style>
      </head>
      <body>
        <div class="email-card">
          <div class="card-header">
            {content_title}
          </div>
          <div class="card-content">
            <p>{hello}</p>
            <div class="message-content">
              {message}
            </div>
            <p>If you're unsure what this email is about, feel free to ignore it.</p>
            <div class="send-time">
              Send Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </div>
          </div>
          <div class="footer-note">
            This email is automatically sent by the system, please do not reply directly<br>All rights reserved © {datetime.now().year}
          </div>
        </div>
      </body>
    </html>
    """
    return content

def get_info_html(task, device_info, ip_info):
    info_html = f"""
    <table border="0" cellspacing="3" cellpadding="0" style="display: inline-table;">
      <tr>
        <td style="text-align: left; font-weight: normal; padding-right: 8px;">DEVICE INFO:</td>
        <td>{device_info}</td>
      </tr>
      <tr>
        <td style="text-align: left; font-weight: normal; padding-right: 8px;">IP INFO:</td>
        <td>{ip_info}</td>
      </tr>
      <tr>
        <td style="text-align: left; font-weight: normal; padding-right: 8px;">TASK NAME:</td>
        <td>{task.get(Key.TaskName, Key.Unknown)}</td>
      </tr>
      <tr>
        <td style="text-align: left; font-weight: normal; padding-right: 8px;">TRIGGER TYPE:</td>
        <td>{task.get(Key.TriggerType, Key.Unknown)}</td>
      </tr>
      <tr>
        <td style="text-align: left; font-weight: normal; padding-right: 8px;">OPERATION:</td>
        <td>{task.get(Key.Operation, Key.Unknown)}</td>
      </tr>
      <tr>
        <td style="text-align: left; font-weight: normal; padding-right: 8px;">EXECUTE DAY:</td>
        <td>{task.get(Key.ExecuteDay, QDate.currentDate().toString('yyyy-MM-dd'))}</td>
      </tr>
      <tr>
        <td style="text-align: left; font-weight: normal; padding-right: 8px;">SCHEDULED TIME:</td>
        <td>{f"{task.get(Key.ExecuteTime, Key.Unknown)}{'' if not task.get(Key.TimeOffset) else f' - {Utils.hour_min_str_add_seconds(task.get(Key.ExecuteTime), task.get(Key.TimeOffset))}'}"}</td>
      </tr>
      <tr>
        <td style="text-align: left; font-weight: normal; padding-right: 8px;">ACTUAL FINISHED:</td>
        <td>{f'{datetime.now().strftime("%H:%M")} (Cost: {task.get(Key.CostTime)}s)'}</td>
      </tr>
    </table>
    """
    return info_html

if __name__ == "__main__":
    task = {
        "task_name": "AutoClock_Windows_Plan",
        "task_id": "2025_11_08_19_54_47_920866",
        "operation": "Shut Down Windows",
        "trigger_type": "Once",
        "execute_time": "19:55",
        "system_plan_name": "AutoClock_Windows_Plan_Type_Once_Date_2025_11_08_Time_19_55_Id_2025_11_08_19_54_47_920866",
        "execute_day": "2025-11-08",
        Key.TimeOffset: 3960,
    }
    email = "1351763110@qq.com"
    ok, error = False, "Unknown Error"
    send_email_by_result(task, email,True,True, ok, error)