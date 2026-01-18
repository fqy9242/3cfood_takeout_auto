import requests
import time
import json
import random
import os
import sys

# 配置文件路径
CONFIG_FILE = "accounts.json"


class CampusFoodBot:
    def __init__(self, account_config):
        """
        初始化机器人
        :param account_config: 包含账号信息的字典 (token, note)
        """
        self.token = account_config.get("token")
        # 如果配置文件里没有备注，默认显示 Unknown
        self.account_note = account_config.get("note", "Unknown Account")

        self.host = "https://waimai.3cfood.com"
        # 抓包分析得到的固定推广ID
        self.spread_token = "o82pvx"

        # 伪装成微信小程序客户端的请求头
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
        """格式化日志输出，带有账号备注前缀"""
        print(f"[{self.account_note}] {message}")

    def sign_in(self):
        """执行每日签到任务"""
        self.log(">>> Starting daily sign-in...")
        api = "/user/v3/Sign/signIn"
        params = {
            "is_register_user": 1,
            "spread_token": self.spread_token,
            "shop_token": "",
            "agent_token": ""
        }
        try:
            resp = requests.get(self.host + api, headers=self.headers, params=params)
            data = resp.json()
            if data.get("code") == 1000:
                self.log("✅ Sign-in successful.")
            else:
                self.log(f"⚠️ Sign-in response: {data.get('msg')}")
        except Exception as e:
            self.log(f"❌ Sign-in error: {e}")

    def get_shop_list(self):
        """获取店铺列表，用于后续的收藏任务"""
        self.log(">>> Fetching shop list...")
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
            resp = requests.get(self.host + api, headers=self.headers, params=params)
            data = resp.json()

            if data.get("code") == 1000 and "data" in data:
                return data["data"]["data"]
            else:
                self.log(f"⚠️ Failed to get shop list: {data.get('msg')}")
                return []
        except Exception as e:
            self.log(f"❌ Network error getting shop list: {e}")
            return []

    def manage_collection(self, shop_info, action="save"):
        """
        执行收藏或取消收藏操作
        :param shop_info: 店铺信息字典
        :param action: 'save' 为收藏, 'del' 为取消
        """
        if action == "save":
            api = "/user/v1/user/saveUserCollection"
            action_text = "Collect"
        else:
            api = "/user/v1/user/delUserCollection"
            action_text = "Un-collect"

        # [cite_start]构造请求体 [cite: 7, 11]
        payload = {
            "is_register_user": 1,
            "spread_token": self.spread_token,
            "shop_token": shop_info.get("shop_token"),
            "agent_token": "",
            "shop_id": shop_info.get("shop_id"),
            "spread_id": shop_info.get("spread_id", 121919)
        }

        try:
            resp = requests.post(self.host + api, headers=self.headers, json=payload)
            data = resp.json()
            shop_name = shop_info.get('shop_name', 'Unknown Shop')

            if data.get("code") == 1000:
                self.log(f"✅ [{shop_name}] {action_text} success")
            else:
                self.log(f"⚠️ [{shop_name}] {action_text} failed: {data.get('msg')}")
        except Exception as e:
            self.log(f"❌ Request error ({action_text}): {e}")

    def run(self):
        """单个账号的主执行流程"""
        self.log("🚀 Starting tasks...")

        # 1. 每日签到
        self.sign_in()
        time.sleep(random.randint(1, 3))

        # 2. 获取店铺列表
        shops = self.get_shop_list()
        if not shops:
            self.log("❌ No shops found, aborting collection tasks.")
            return

        # 3. 处理前5个店铺 (每日积分上限通常为5次)
        target_shops = shops[:5]
        self.log(f"📋 Found {len(shops)} shops, processing top {len(target_shops)}...")

        for index, shop in enumerate(target_shops):
            # A步骤: 收藏店铺 (获取积分)
            self.manage_collection(shop, action="save")

            # 随机延迟，模拟真人浏览
            time.sleep(random.randint(2, 4))

            # B步骤: 取消收藏 (为了明天能重复刷分)
            self.manage_collection(shop, action="del")

            # 店铺之间的操作间隔
            time.sleep(random.randint(1, 2))

        self.log("🎉 All tasks completed for this account.\n")


def load_config():
    """从 JSON 文件加载账号配置"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Error: Config file '{CONFIG_FILE}' not found.")
        print("Please create it. Format: [{'note': 'name', 'token': '...'}]")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: '{CONFIG_FILE}' is not valid JSON.")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 50)
    print("   Campus Food Delivery Auto-Bot")
    print("   校园外卖自动任务脚本")
    print("=" * 50)

    accounts = load_config()
    print(f"📂 Loaded {len(accounts)} accounts from config.\n")

    for idx, account_cfg in enumerate(accounts):
        if not account_cfg.get("token"):
            print(f"⚠️ Skipping account #{idx + 1} due to missing token.")
            continue

        try:
            bot = CampusFoodBot(account_cfg)
            bot.run()
        except Exception as e:
            print(f"❌ Critical error running account {account_cfg.get('note')}: {e}")

        # 多账号切换时的防封控延迟
        if idx < len(accounts) - 1:
            wait_time = random.randint(3, 6)
            print(f"⏳ Waiting {wait_time}s before next account...")
            time.sleep(wait_time)

    print("=" * 50)
    print("✅ Batch processing finished.")