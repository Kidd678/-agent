from app.services.intent import IntentClassifier

queries = [
    "帮我查一下明天北京天气",
    "量子纠缠是什么意思",
    "你好呀",
    "打开相机",
    "最近有什么热门新闻",
    "导航去最近的地铁站",
]

for q in queries:
    result = IntentClassifier.predict_sync(q)
    print(f"{q}  ->  {result.label}  (raw: {result.raw_output})")
