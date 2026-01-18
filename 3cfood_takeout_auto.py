import requests
import time
import json
import random


class CampusFoodBot:
    def __init__(self, token):
        self.host = "https://waimai.3cfood.com"
        # 核心请求头
        self.headers = {
            "Host": "waimai.3cfood.com",
            "Connection": "keep-alive",
            "Authorization": token,
            "version": "4.12.12",
            "canary_o2o_mini": "o82pvx",
            "visit-from": "2",
            "Content-Type": "application/json;charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; M2006J10C Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 XWEB/1160285 MMWEBSDK/20251006 MMWEBID/2295 MicroMessenger/8.0.66.2963(0x28004243) WeChat/arm64 Weixin GPVersion/1 NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android"
        }
        # 你的 spread_token (推广ID)，从抓包URL看是固定的
        self.spread_token = "o82pvx"

    def sign_in(self):
        """每日签到"""
        print(">>> 正在执行签到...")
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
                print(f"✅ 签到成功！当前积分可能+1")
            else:
                print(f"⚠️ 签到结果: {data.get('msg')}")
        except Exception as e:
            print(f"❌ 签到出错: {e}")

    def get_shop_list(self):
        """获取店铺列表"""
        print(">>> 正在获取店铺列表...")
        api = "/mall/v2/ShopIndex/getShopListInSortV2"
        # 参考 Source 4 的参数，把 page 改成 1
        params = {
            "is_register_user": 1,
            "spread_token": self.spread_token,
            "page": 1,
            "size": 10,  # 获取10个够用了
            "type": 0,
            "sort_id": 50103,  # 从抓包里提取的分类ID
            "sort_type": 1,
            # 经纬度坐标，直接用抓包里的，似乎跟学校有关
            "tag": "108.24513292100694,22.84365749782986"
        }

        try:
            resp = requests.get(self.host + api, headers=self.headers, params=params)
            data = resp.json()

            if data.get("code") == 1000 and "data" in data:
                # 提取店铺列表，返回前5个
                shop_list = data["data"]["data"]
                return shop_list
            else:
                print(f"⚠️ 获取店铺列表失败: {data.get('msg')}")
                return []
        except Exception as e:
            print(f"❌ 获取店铺列表请求异常: {e}")
            return []

    def manage_collection(self, shop_info, action="save"):
        """
        收藏/取消收藏 单个店铺
        shop_info: 包含 shop_id, shop_token 等信息的字典
        action: 'save' (收藏) 或 'del' (取消)
        """
        if action == "save":
            api = "/user/v1/user/saveUserCollection"
            action_text = "收藏"
        else:
            api = "/user/v1/user/delUserCollection"
            action_text = "取消"

        # 构造请求体，数据从 shop_info 动态获取 [cite: 7, 11]
        payload = {
            "is_register_user": 1,
            "spread_token": self.spread_token,
            "shop_token": shop_info.get("shop_token"),
            "agent_token": "",
            "shop_id": shop_info.get("shop_id"),
            "spread_id": shop_info.get("spread_id", 121919)  # 默认值以防万一
        }

        try:
            resp = requests.post(self.host + api, headers=self.headers, json=payload)
            data = resp.json()
            shop_name = shop_info.get('shop_name', '未知店铺')

            if data.get("code") == 1000:
                print(f"✅ [{shop_name}] {action_text}成功")
            else:
                print(f"⚠️ [{shop_name}] {action_text}失败: {data.get('msg')}")
        except Exception as e:
            print(f"❌ 请求异常: {e}")

    def run(self):
        print("=" * 30)
        print("🚀 校园外卖自动任务开始")
        print("=" * 30)

        # 1. 先签到
        self.sign_in()
        time.sleep(random.randint(1, 3))

        # 2. 获取店铺列表
        shops = self.get_shop_list()

        if not shops:
            print("❌ 没有获取到店铺，任务终止")
            return

        # 3. 循环处理前 5 个店铺
        # 即使返回的店铺很多，我们也只取前 5 个，因为每日积分上限通常是 5 次
        target_shops = shops[:5]
        print(f"📋 获取到 {len(shops)} 家店铺，将对前 {len(target_shops)} 家执行刷分...")

        for index, shop in enumerate(target_shops):
            print(f"\n--- 正在处理第 {index + 1} 家店铺 ---")

            # 第一步：收藏 (拿积分)
            self.manage_collection(shop, action="save")

            # 随机等待 2-4 秒，模拟真人操作，防止过快被封
            time.sleep(random.randint(2, 4))

            # 第二步：取消收藏 (为了明天能继续刷)
            self.manage_collection(shop, action="del")

            # 店铺间稍微间隔一下
            time.sleep(random.randint(1, 2))

        print("\n" + "=" * 30)
        print("🎉 今日所有任务执行完毕！")
        print("=" * 30)


if __name__ == "__main__":
    MY_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzcHJlYWRfaWQiOjEyMTkxOSwic2hvcF9pZCI6MCwidXNlcl9pZCI6MTE2MzM3NDAsImxvZ2luX3Rlcm1pbmFsIjoxLCJsb2dpbl9ndWlkIjoiIiwiYXVkIjoiXC9hcGlcL2NvbW1vblwvdXNlckxvZ2luIiwiZXhwIjoxNzY5MTY1MjM0LCJpYXQiOjE3Njg3MzMyMzQsImlzcyI6Imh0dHBzOlwvXC93YWltYWkuM2Nmb29kLmNvbSIsImp0aSI6IjBiZDQ4NDJlNGE5MjkwOGQyNGJiMmM1MDg1YjNkNDZiIn0.82p31dSJUtlEy6DgYJuIplSQEIlrUh0Hwq2uAxlBWUM"
    bot = CampusFoodBot(MY_TOKEN)
    bot.run()