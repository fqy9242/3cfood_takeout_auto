import requests
import time
import json
import random
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from datetime import datetime

# ================= 配置文件路径 =================
ACCOUNTS_FILE = "accounts.json"
SMTP_CONFIG_FILE = "smtp_config.json"


# ==============================================

class CampusFoodBot:
    def __init__(self, account_config, smtp_config):
        self.account = account_config
        self.token = account_config.get("token")
        self.account_note = account_config.get("note", "未知账号")
        self.smtp_config = smtp_config  # 传入SMTP配置

        self.host = "https://waimai.3cfood.com"
        self.spread_token = "o82pvx"
        self.headers = {
            "Host": "waimai.3cfood.com",
            "Connection": "keep-alive",
            "Authorization": self.token,
            "version": "4.12.12",
            "canary_o2o_mini": self.spread_token,
            "visit-from": "2",
            "Content-Type": "application/json;charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; M2006J10C Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 XWEB/1160285 MMWEBSDK/20251006 MMWEBID/2295 MicroMessenger/8.0.66.2963(0x28004243) WeChat/arm64 Weixin GPVersion/1 NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android"
        }

    def log(self, message):
        """格式化日志输出"""
        print(f"[{self.account_note}] {message}")

    def send_notification(self, title, content):
        """发送 SMTP 邮件通知 (支持配置分离)"""
        # 1. 检查接收者邮箱
        if 'email' not in self.account or not self.account['email']:
            return

        # 2. 检查 SMTP 配置是否存在
        if not self.smtp_config:
            self.log("⚠️ 未检测到 smtp_config.json，跳过邮件发送")
            return

        sender = self.smtp_config.get('sender_email')
        password = self.smtp_config.get('sender_pass')
        host = self.smtp_config.get('smtp_server', 'smtp.qq.com')
        port = self.smtp_config.get('smtp_port', 465)
        receiver = self.account['email']

        if not sender or not password:
            self.log("⚠️ SMTP 配置不完整，请检查 smtp_config.json")
            return

        try:
            # 标准化发件人格式，解决 550 错误
            from_addr = formataddr(["外卖助手", sender])
            to_addr = formataddr(["用户", receiver])

            message = MIMEText(content, 'html', 'utf-8')
            message['From'] = from_addr
            message['To'] = to_addr
            message['Subject'] = Header(title, 'utf-8')

            # 连接 SMTP
            smtp_obj = smtplib.SMTP_SSL(host, port, timeout=10)
            smtp_obj.login(sender, password)
            smtp_obj.sendmail(sender, [receiver], message.as_string())
            smtp_obj.quit()

            self.log(f"✅ 邮件通知已发送至 {receiver}")
        except Exception as e:
            self.log(f"❌ 邮件发送失败: {e}")

    def get_user_info(self):
        """获取用户信息及积分余额"""
        url = "https://waimai.3cfood.com/user/v1/user/getUserInfo"
        params = {
            "is_register_user": "1",
            "show_more": "true"
        }
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)

            if resp.status_code == 401:
                return None, None, False

            data = resp.json()
            if data.get('code') == 1000:
                score = data['data'].get('score', '未知')
                nickname = data['data'].get('nick_name', '用户')
                self.log(f"💰 当前积分: {score}")
                return nickname, score, True
        except Exception as e:
            self.log(f"❌ 获取积分信息失败: {e}")

        return "未知", "未知", True

    def sign_in(self):
        """执行每日签到"""
        self.log("⏳ 正在执行每日签到...")
        api = "/user/v3/Sign/signIn"
        params = {
            "is_register_user": 1,
            "spread_token": self.spread_token,
            "shop_token": "",
            "agent_token": ""
        }
        try:
            resp = requests.get(self.host + api, headers=self.headers, params=params, timeout=15)

            if resp.status_code == 401:
                self.log("❌ Token 已失效 (401 Unauthorized)")
                return False

            data = resp.json()
            if data.get("code") == 1000:
                self.log("✅ 签到成功")
            else:
                self.log(f"⚠️ 签到返回异常: {data.get('msg')}")
            return True
        except Exception as e:
            self.log(f"❌ 签到请求错误: {e}")
            return True

    def get_shop_list(self):
        """获取店铺列表"""
        self.log("⏳ 正在获取店铺列表...")
        api = "/mall/v2/ShopIndex/getShopListInSortV2"
        params = {
            "is_register_user": 1,
            "spread_token": self.spread_token,
            "page": 1,
            "size": 10,
            "type": 0,
            "sort_id": 50103,
            "sort_type": 1,
            "tag": "108.24513292100694,22.84365749782986"
        }

        try:
            resp = requests.get(self.host + api, headers=self.headers, params=params, timeout=15)
            data = resp.json()

            if data.get("code") == 1000 and "data" in data:
                return data["data"]["data"]
            else:
                self.log(f"⚠️ 获取店铺列表失败: {data.get('msg')}")
                return []
        except Exception as e:
            self.log(f"❌ 获取店铺列表网络错误: {e}")
            return []

    def manage_collection(self, shop_info, action="save"):
        """收藏或取消收藏操作"""
        if action == "save":
            api = "/user/v1/user/saveUserCollection"
            action_text = "收藏"
        else:
            api = "/user/v1/user/delUserCollection"
            action_text = "取消收藏"

        payload = {
            "is_register_user": 1,
            "spread_token": self.spread_token,
            "shop_token": shop_info.get("shop_token"),
            "agent_token": "",
            "shop_id": shop_info.get("shop_id"),
            "spread_id": shop_info.get("spread_id", 121919)
        }

        try:
            resp = requests.post(self.host + api, headers=self.headers, json=payload, timeout=15)
            data = resp.json()
            shop_name = shop_info.get('shop_name', '未知店铺')

            if data.get("code") == 1000:
                self.log(f"✅ [{shop_name}] {action_text}成功")
            else:
                self.log(f"⚠️ [{shop_name}] {action_text}失败: {data.get('msg')}")
        except Exception as e:
            self.log(f"❌ 请求错误 ({action_text}): {e}")

    def run(self):
        """主任务流程"""
        self.log("🚀 开始执行任务...")

        nickname, start_score, token_valid = self.get_user_info()

        # Token 失效处理
        if not token_valid:
            self.send_notification(
                title=f"【报警】校邦Token失效-{self.account_note}",
                content=f"账号：{self.account_note}<br>状态：Token已过期，请重新抓包更新！<br>时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            return

        # 签到
        if not self.sign_in():
            self.send_notification(
                title=f"【报警】校邦Token失效-{self.account_note}",
                content=f"账号：{self.account_note}<br>状态：Token已过期，请重新抓包更新！<br>时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            return

        time.sleep(random.randint(1, 3))

        # 收藏任务
        shops = self.get_shop_list()
        if not shops:
            self.log("❌ 未找到店铺，停止收藏任务")
            return

        target_shops = shops[:5]
        self.log(f"📋 获取到 {len(shops)} 个店铺，将处理前 {len(target_shops)} 个...")

        for index, shop in enumerate(target_shops):
            self.manage_collection(shop, action="save")
            time.sleep(random.randint(2, 4))
            self.manage_collection(shop, action="del")
            time.sleep(random.randint(1, 2))

        self.log("🎉 该账号所有任务已完成")

        # 任务完成通知
        final_nickname, final_score, _ = self.get_user_info()
        if final_score != "未知":
            self.send_notification(
                title=f"校邦任务完成-{self.account_note}",
                content=(
                    f"用户：{final_nickname}<br>"
                    f"状态：✅ 今日任务已完成<br>"
                    f"当前积分余额：<b style='color:red;font-size:20px'>{final_score}</b><br>"
                    f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
            )


def load_json(file_path):
    """通用JSON加载函数"""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ 错误: '{file_path}' JSON 格式不正确")
        return None


if __name__ == "__main__":
    print("=" * 50)
    print("   校园外卖自动任务脚本 (Campus Food Auto-Bot)")
    print("=" * 50)

    # 1. 加载账号
    accounts = load_json(ACCOUNTS_FILE)
    if not accounts:
        print(f"❌ 找不到或无法读取 {ACCOUNTS_FILE}，请检查配置。")
        sys.exit(1)

    # 2. 加载SMTP配置 (允许为空，为空则不发邮件)
    smtp_config = load_json(SMTP_CONFIG_FILE)
    if not smtp_config:
        print(f"⚠️ 未检测到 {SMTP_CONFIG_FILE}，邮件通知功能将禁用。")

    print(f"📂 已加载 {len(accounts)} 个账号配置\n")

    for idx, account_cfg in enumerate(accounts):
        if not account_cfg.get("token"):
            print(f"⚠️ 跳过第 {idx + 1} 个账号：缺少 Token")
            continue

        try:
            # 将 smtp_config 传给 Bot
            bot = CampusFoodBot(account_cfg, smtp_config)
            bot.run()
        except Exception as e:
            print(f"❌ 账号 {account_cfg.get('note')} 运行发生严重错误: {e}")

        if idx < len(accounts) - 1:
            wait_time = random.randint(3, 6)
            print(f"⏳ 等待 {wait_time} 秒后执行下一个账号...")
            time.sleep(wait_time)

    print("=" * 50)
    print("✅ 所有账号批量处理完毕")