INTENT_LABELS = {
    "tool_call": "工具调用",
    "knowledge_qa": "知识问答",
    "chitchat": "闲聊",
    "system_op": "系统操作",
    "web_search": "网络搜索",
    "navigation": "导航出行",
}

INTENT_LIST = list(INTENT_LABELS.keys())

CLASSIFICATION_PROMPT = (
    "判断以下用户输入的意图类别，只输出类别名称。\n"
    "类别：tool_call / knowledge_qa / chitchat / system_op / web_search / navigation"
)
