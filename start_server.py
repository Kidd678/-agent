"""启动主服务 + 意图分类子服务。

用法：
    python start_server.py           # 启动两个服务
    python start_server.py --main    # 仅启动主服务（假设分类服务已在运行）
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main", action="store_true", help="仅启动主服务")
    parser.add_argument("--intent-only", action="store_true", help="仅启动分类服务")
    parser.add_argument("--intent-port", type=int, default=8001)
    parser.add_argument("--main-port", type=int, default=8000)
    args = parser.parse_args()

    processes = []

    if not args.main:
        # 启动意图分类子服务
        print(f"Starting intent service on :{args.intent_port} ...")
        p = subprocess.Popen(
            [sys.executable, str(PROJECT_ROOT / "intent_service.py"), "--port", str(args.intent_port)],
            cwd=str(PROJECT_ROOT),
        )
        processes.append(("intent_service", p))
        # 等待子服务加载模型
        time.sleep(2)

    if not args.intent_only:
        # 启动主服务
        print(f"Starting main service on :{args.main_port} ...")
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(args.main_port)],
            cwd=str(PROJECT_ROOT),
        )
        processes.append(("main", p))

    try:
        for name, p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        for name, p in processes:
            p.terminate()


if __name__ == "__main__":
    main()
