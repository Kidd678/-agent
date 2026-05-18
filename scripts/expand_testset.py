"""将 retrieval_testset.json 从 50 条扩展到 200 条。

策略：
1. 保留原始 50 条
2. 为每个工具生成口语化变体 query（4-5 条/工具）
3. 难负例从语义相近工具中选取 3-4 个
4. 最终去重，取 200 条
"""

import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "tools" / "registry.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "tool_test" / "retrieval_testset.json"

# ── 工具 → 口语化 query 模板 ──────────────────────────────
# 每个工具 4-5 个变体，覆盖不同说法
QUERY_VARIANTS = {
    "weather_query": [
        "查一下明天北京天气",
        "今天上海多少度",
        "帮我看看广州明天会不会下雨",
        "深圳今天天气怎么样",
        "杭州明天适合出门吗",
        "查查成都今天的温度",
        "今天会下雨吗",
        "帮我看看天气",
    ],
    "weather_forecast": [
        "北京未来一周天气",
        "上海未来几天天气预报",
        "帮我看看这周的天气趋势",
        "深圳接下来一周会降温吗",
        "查看未来7天天气",
        "成都这周天气怎么样",
    ],
    "weather_alert": [
        "今天有暴雨预警吗",
        "查看台风预警",
        "有没有高温预警",
        "今天有天气预警吗",
        "帮我看看有没有恶劣天气预警",
        "北京有沙尘暴预警吗",
    ],
    "alarm_set": [
        "帮我设置明天早上8点的闹钟",
        "设个7点的闹钟",
        "每天早上6点半叫我起床",
        "设一个下午3点的闹钟",
        "帮我定个闹钟明早7点",
        "设个闹钟半小时后响",
        "明天早上叫我起来",
    ],
    "alarm_delete": [
        "删除明早的闹钟",
        "取消7点的闹钟",
        "把明天早上的闹钟删了",
        "帮我删掉那个下午3点的闹钟",
        "取消所有闹钟",
    ],
    "alarm_list": [
        "我设置了哪些闹钟",
        "查看所有闹钟",
        "看看我现在有几个闹钟",
        "闹钟列表",
        "帮我看看闹钟",
    ],
    "timer_set": [
        "计时5分钟",
        "设置10分钟倒计时",
        "帮我计时30秒",
        "定个15分钟的计时器",
        "倒计时3分钟",
        "帮我设个20分钟的倒计时",
    ],
    "time_query": [
        "现在几点了",
        "纽约现在几点",
        "查看东京时间",
        "帮我看看现在几点",
        "伦敦现在什么时间",
        "当前北京时间",
    ],
    "calendar_create": [
        "记录一下下午3点开会",
        "创建明天上午10点的日程",
        "安排周五下午的会议",
        "帮我建一个明天的日程",
        "下周一上午9点有个面试，帮我记一下",
        "帮我创建一个会议日程",
    ],
    "calendar_query": [
        "今天有什么日程",
        "查看明天的日程",
        "这周有什么会议",
        "帮我看看今天的安排",
        "明天有什么日程",
        "查看一下我的日历",
    ],
    "calendar_delete": [
        "删除明天的日程",
        "取消下午的会议",
        "把周五的会议删了",
        "帮我取消明天的安排",
        "删掉那个日程",
    ],
    "reminder_set": [
        "设置每周一的提醒",
        "提醒我下午交报告",
        "明天早上提醒我带伞",
        "帮我设个提醒买菜",
        "提醒我晚上8点吃药",
        "设置一个生日提醒",
    ],
    "phone_call": [
        "帮我打电话给张三",
        "拨打13800138000",
        "给妈妈打电话",
        "打电话给老板",
        "帮我拨个电话",
        "呼叫张三",
    ],
    "phone_call_log": [
        "查看最近的通话",
        "今天谁给我打过电话",
        "看看最近的通话记录",
        "查一下昨天的来电",
        "查看通话历史",
    ],
    "sms_send": [
        "发短信给妈妈说我晚点到",
        "给张三发短信说我到了",
        "发条短信给老板请假",
        "帮我发短信说明天不去",
        "发短信给13800138000",
    ],
    "sms_read": [
        "查看最近短信",
        "有没有张三发的短信",
        "看看今天收到的短信",
        "帮我查一下短信",
        "查看未读短信",
    ],
    "contact_query": [
        "查一下张三的电话",
        "找一下李四的联系方式",
        "帮我查个号码",
        "张三的手机号是多少",
        "帮我找一下王五的电话",
    ],
    "contact_add": [
        "帮我存一下这个号码",
        "添加新联系人",
        "保存13800138000为张三",
        "帮我把这号码存起来",
        "新建一个联系人",
    ],
    "navigation_start": [
        "导航去机场",
        "怎么去故宫",
        "帮我导航到北京南站",
        "带我去最近的地铁站",
        "导航去公司",
        "开车去三里屯",
    ],
    "navigation_nearby": [
        "附近有什么好吃的",
        "附近有加油站吗",
        "找一下附近的餐厅",
        "最近的停车场在哪",
        "附近有药店吗",
        "帮我找找附近的咖啡店",
        "附近有没有超市",
    ],
    "navigation_route": [
        "从北京到上海怎么走",
        "帮我规划路线",
        "从公司到机场怎么走",
        "规划一下去上海的路线",
        "去火车站走哪条路最快",
        "帮我看看怎么去那个地方",
    ],
    "navigation_eta": [
        "到公司要多久",
        "到机场要多久",
        "现在出发去公司几点能到",
        "去首都机场需要多长时间",
        "帮我算一下到那儿要多久",
    ],
    "navigation_parking": [
        "附近有停车场吗",
        "附近哪里可以停车",
        "找一下商场的停车场",
        "帮我找个停车位",
        "最近的停车场在哪",
    ],
    "navigation_weather_road": [
        "三环堵车吗",
        "京藏高速路况怎么样",
        "帮我看看长安街堵不堵",
        "今天四环路况如何",
        "去机场那条路堵车吗",
    ],
    "navigation_bus": [
        "查一下公交到站时间",
        "300路公交什么时候到",
        "下一班公交还有多久",
        "帮我看看52路还有几站",
        "查一下附近公交站",
    ],
    "navigation_subway": [
        "地铁怎么换乘",
        "从西直门到国贸怎么换乘",
        "查一下地铁路线",
        "帮我看看坐地铁怎么去",
        "地铁几号线能到天安门",
    ],
    "navigation_flight": [
        "查一下航班信息",
        "查一下CA1234航班",
        "今天有去上海的航班吗",
        "帮我看看明天的航班",
        "查一下从北京飞深圳的航班",
    ],
    "navigation_train": [
        "明天去上海的高铁",
        "查一下明天去上海的高铁",
        "北京到广州的火车票",
        "帮我看看有没有去杭州的动车",
        "查一下火车票",
        "买一张去南京的高铁票",
    ],
    "system_wifi": [
        "打开WiFi",
        "关闭无线网络",
        "连一下WiFi",
        "帮我打开wifi",
        "把wifi关了",
    ],
    "system_bluetooth": [
        "关闭蓝牙",
        "打开蓝牙",
        "帮我把蓝牙关了",
        "连一下蓝牙",
        "蓝牙开了吗",
    ],
    "system_brightness": [
        "把屏幕亮度调高",
        "调高亮度",
        "把亮度调到50%",
        "开启自动亮度",
        "屏幕太暗了帮我调亮一点",
        "把亮度调低一点",
    ],
    "system_volume": [
        "调低音量",
        "把铃声调小一点",
        "静音",
        "音量调到最大",
        "帮我把媒体音量调小",
        "把音量关了",
    ],
    "system_flashlight": [
        "打开手电筒",
        "关闭闪光灯",
        "帮我开手电筒",
        "把手电筒关了",
        "开一下闪光灯",
    ],
    "system_camera": [
        "打开相机拍照",
        "我要拍照",
        "录个视频",
        "帮我打开前置摄像头",
        "切换到自拍模式",
    ],
    "system_screenshot": [
        "截个屏",
        "截屏",
        "帮我截图",
        "截一下当前屏幕",
        "截个图",
    ],
    "system_dnd": [
        "开启勿扰模式",
        "关闭免打扰",
        "帮我开勿扰",
        "开启免打扰一小时",
        "把勿扰关了",
    ],
    "system_nfc": [
        "打开NFC",
        "关闭NFC",
        "帮我把NFC打开",
        "NFC功能开了吗",
        "把NFC关掉",
    ],
    "system_rotation": [
        "关闭自动旋转",
        "锁定屏幕旋转",
        "开启自动旋转",
        "帮我把屏幕旋转关了",
        "把自动旋转打开",
    ],
    "web_search": [
        "帮我查一下快递",
        "搜索Python教程",
        "帮我搜一下附近的酒店",
        "搜索一下减肥方法",
        "帮我查一下明天的限号",
        "搜一下怎么做红烧肉",
        "帮我查查这个单词什么意思",
    ],
    "web_news": [
        "今天有什么新闻",
        "查看科技新闻",
        "体育新闻",
        "帮我看看今天的热点新闻",
        "有什么国际新闻",
        "看看最新的财经新闻",
    ],
    "web_stock": [
        "茅台股价多少",
        "查一下今天的股票",
        "查一下茅台股价",
        "苹果股票多少钱",
        "帮我看看A股今天怎么样",
        "查一下比亚迪股价",
    ],
    "web_exchange": [
        "查一下美元汇率",
        "美元兑人民币汇率",
        "100欧元换多少日元",
        "帮我看看今天的汇率",
        "日元兑人民币多少",
    ],
    "web_translate": [
        "翻译这句话成英文",
        "把这句话翻译成英文",
        "翻译'你好'成日语",
        "帮我翻译一下这段话",
        "把这段中文翻成法语",
    ],
    "web_encyclopedia": [
        "什么是量子力学",
        "什么是量子计算",
        "黑洞是什么",
        "介绍一下人工智能",
        "帮我查查光合作用是什么",
        "DNA是什么",
    ],
    "web_recipe": [
        "红烧肉怎么做",
        "教我做宫保鸡丁",
        "糖醋排骨的做法",
        "帮我查一下番茄炒蛋怎么做",
        "可乐鸡翅怎么做",
        "有没有简单的家常菜推荐",
    ],
    "web_movie": [
        "搜索一下最新的电影",
        "最近有什么好看的电影",
        "流浪地球评分多少",
        "帮我查一下热映电影",
        "有什么好看的科幻片推荐",
    ],
    "web_music": [
        "播放轻音乐",
        "播放周杰伦的歌",
        "来一首轻音乐",
        "帮我放一首歌",
        "播放一些放松的音乐",
        "搜索一下Taylor Swift的歌",
    ],
    "web_encyclopedia": [
        "地球到月球有多远",
        "水的沸点是多少度",
        "光速是多少",
        "帮我解释一下相对论",
        "中国有多少个省",
        "珠穆朗玛峰有多高",
    ],
}

# ── 难负例分组（语义相近的工具） ─────────────────────────
TOOL_GROUPS = {
    "time": ["alarm_set", "alarm_delete", "alarm_list", "timer_set", "time_query"],
    "calendar": ["calendar_create", "calendar_query", "calendar_delete", "reminder_set"],
    "comm": ["phone_call", "phone_call_log", "sms_send", "sms_read", "contact_query", "contact_add"],
    "nav": ["navigation_start", "navigation_nearby", "navigation_route", "navigation_eta", "navigation_parking", "navigation_weather_road"],
    "transit": ["navigation_bus", "navigation_subway", "navigation_flight", "navigation_train"],
    "system": ["system_wifi", "system_bluetooth", "system_brightness", "system_volume", "system_flashlight", "system_camera", "system_screenshot", "system_dnd", "system_nfc", "system_rotation"],
    "web_info": ["web_search", "web_news", "web_stock", "web_exchange"],
    "web_content": ["web_translate", "web_encyclopedia", "web_recipe", "web_movie", "web_music"],
    "weather": ["weather_query", "weather_forecast", "weather_alert"],
    "knowledge": ["web_encyclopedia", "web_search"],
}

def get_hard_negatives(tool_id: str, n: int = 3) -> list[str]:
    """从同组工具中选取难负例。"""
    group = None
    for g, members in TOOL_GROUPS.items():
        if tool_id in members:
            group = [m for m in members if m != tool_id]
            break

    if not group:
        # 从所有工具中随机选
        all_tools = [t for tool_list in TOOL_GROUPS.values() for t in tool_list]
        group = [t for t in all_tools if t != tool_id]

    random.seed(hash(tool_id))
    return random.sample(group, min(n, len(group)))


def main():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)["tools"]

    all_tool_ids = [t["id"] for t in registry]

    # 加载原始测试集
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        original = json.load(f)

    # 构建扩展测试集
    expanded = list(original)  # 保留原始 50 条

    seen_queries = {c["query"] for c in expanded}

    for tool_id, variants in QUERY_VARIANTS.items():
        if tool_id not in all_tool_ids:
            continue
        negatives = get_hard_negatives(tool_id, 4)
        for q in variants:
            if q not in seen_queries:
                expanded.append({
                    "query": q,
                    "positive_tool_ids": [tool_id],
                    "hard_negative_tool_ids": negatives,
                })
                seen_queries.add(q)

    # 随机打乱，取 200 条
    random.seed(42)
    random.shuffle(expanded)
    expanded = expanded[:200]

    # 统计覆盖
    covered = set()
    for c in expanded:
        covered.update(c["positive_tool_ids"])

    print(f"Total cases: {len(expanded)}")
    print(f"Tools covered: {len(covered)} / {len(all_tool_ids)}")
    missing = set(all_tool_ids) - covered
    if missing:
        print(f"Missing tools: {missing}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(expanded, f, ensure_ascii=False, indent=2)

    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
