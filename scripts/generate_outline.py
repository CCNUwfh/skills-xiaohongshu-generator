#!/usr/bin/env python3
"""
小红书内容大纲生成脚本
使用 ai-outside-service API 生成小红书图文内容大纲
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import requests

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_API_URL = "http://ai-outside-service.smzdm.com:8000/ai-outside-model/v1/get_chat_data"
DEFAULT_MODEL = "gemini-3.1-pro-preview"
DEFAULT_SOURCE = "ai_skill_all_weifuhe"


def retry_on_error(max_retries=3, base_delay=2):
    """错误自动重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()

                    # 不可重试的错误类型
                    non_retryable = [
                        "401", "unauthenticated", "authentication",  # 认证错误
                        "403", "permission_denied", "forbidden",  # 权限错误
                        "404", "not_found",  # 资源不存在
                        "invalid_argument", "invalid_request",  # 参数错误
                    ]

                    should_retry = True
                    for keyword in non_retryable:
                        if keyword in error_str:
                            should_retry = False
                            break

                    if not should_retry:
                        # 直接抛出，不重试
                        raise

                    # 可重试的错误
                    if attempt < max_retries - 1:
                        if "429" in error_str or "rate" in error_str or "limit" in error_str:
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            logger.warning(f"[重试] 遇到限流，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
class OutlineGenerator:
    """小红书大纲生成器"""

    def __init__(self, api_url: str = None, model: str = None, source: str = None):
        """
        初始化大纲生成器

        Args:
            api_url: API 地址（可选，默认使用预设地址）
            model: 模型名称（可选，默认使用预设模型）
            source: 来源标识（可选，默认使用预设值）
        """
        self.api_url = api_url if api_url else DEFAULT_API_URL
        self.model = model if model else DEFAULT_MODEL
        self.source = source if source else DEFAULT_SOURCE

        logger.info(
            f"OutlineGenerator 初始化: "
            f"api_url={self.api_url}, "
            f"model={self.model}, "
            f"source={self.source}"
        )

    def load_prompt_template(self) -> str:
        """加载提示词模板"""
        template_path = Path(__file__).parent.parent / "references" / "outline-prompt.md"

        if not template_path.exists():
            raise FileNotFoundError(
                f"提示词模板文件不存在: {template_path}\n"
                "请确保 references/outline-prompt.md 文件存在"
            )

        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    def generate_outline(
        self,
        topic: str,
        pages: int = 5
    ) -> str:
        """
        生成小红书内容大纲

        Args:
            topic: 内容主题
            pages: 生成页数（默认为5页）

        Returns:
            生成的大纲文本
        """
        # 加载提示词模板
        prompt_template = self.load_prompt_template()

        # 替换所有占位符
        prompt = prompt_template.replace("{topic}", topic).replace("{pages}", str(pages))

        # 构建请求
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        payload = {
            "model_name": self.model,
            "messages": messages,
            "source": self.source
        }

        headers = {
            "Content-Type": "application/json"
        }

        logger.info(f"调用 API: {self.api_url}, model={self.model}")
        logger.info(f"主题: {topic[:50]}...")

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=300  # 5分钟超时
            )
        except requests.exceptions.Timeout:
            raise Exception(
                "请求超时（5分钟）。\n"
                "可能原因：\n"
                "1. 网络连接不稳定\n"
                "2. API 服务响应过慢\n"
                "解决方案：检查网络连接或稍后重试"
            )
        except requests.exceptions.ConnectionError as e:
            raise Exception(
                f"网络连接失败。\n"
                f"错误详情: {str(e)}\n"
                "可能原因：\n"
                "1. API 地址配置错误\n"
                "2. 网络不可达\n"
                "解决方案：检查 api_url 参数和网络连接"
            )

        # 处理响应
        if response.status_code != 200:
            error_detail = response.text[:500]
            raise Exception(
                f"API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}"
            )

        # 解析响应
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise Exception(
                f"API 返回的不是有效的 JSON 格式\n\n"
                f"【原始响应】{response.text[:500]}"
            )

        # 检查错误码
        error_code = data.get("error_code", -1)
        if error_code != 0:
            error_msg = data.get("error_msg", "未知错误")
            raise Exception(
                f"API 返回错误: error_code={error_code}, error_msg={error_msg}"
            )

        # 提取生成的内容
        result_data = data.get("data", {})
        generated_text = result_data.get("result", "")

        if not generated_text:
            raise Exception(
                "API 返回的内容为空\n\n"
                "【可能原因】\n"
                "1. 模型配置问题\n"
                "2. 请求参数错误"
            )

        logger.info(f"生成成功，输出长度: {len(generated_text)} 字符")
        return generated_text


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="小红书内容大纲生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础用法
  python generate_outline.py \\
    --topic "新手如何学会手冲咖啡"

  # 指定页数
  python generate_outline.py \\
    --topic "春日穿搭指南" \\
    --pages 8

  # 保存到文件
  python generate_outline.py \\
    --topic "主题内容" > output.md
        """
    )

    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API 地址（默认：{DEFAULT_API_URL}）"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"模型名称（默认：{DEFAULT_MODEL}）"
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"来源标识（默认：{DEFAULT_SOURCE}）"
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="内容主题"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="生成页数，默认 5 页"
    )

    args = parser.parse_args()

    try:
        generator = OutlineGenerator(
            api_url=args.api_url,
            model=args.model,
            source=args.source
        )

        outline = generator.generate_outline(
            topic=args.topic,
            pages=args.pages
        )

        # 输出到标准输出
        print(outline)

    except Exception as e:
        logger.error(f"生成失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
