#!/usr/bin/env python3
"""
图片生成 API 调用脚本
使用 openai-cv-service 生成图片
"""

import argparse
import json
import logging
import os
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_API_URL = "http://openai-cv-service.smzdm.com:809/pictures/create_img"
DEFAULT_MODEL = "img_6_2_20251124_v3"
DEFAULT_UPLOAD_CONFIG = {
    "channel": 29,
    "type": "linkstars",
    "oper": "aigc"
}


class ImageGenerator:
    """图片生成器类"""

    def __init__(self, api_url: str = None, model: str = None):
        """
        初始化图片生成器

        Args:
            api_url: API 地址（可选，默认使用预设地址）
            model: 模型名称（可选，默认使用预设模型）
        """
        self.api_url = api_url if api_url else DEFAULT_API_URL
        self.model = model if model else DEFAULT_MODEL
        self.upload_config = DEFAULT_UPLOAD_CONFIG

        logger.info(
            f"ImageGenerator 初始化: "
            f"api_url={self.api_url}, "
            f"model={self.model}"
        )

    def generate_image(self, prompt: str, output_path: str) -> str:
        """
        生成图片

        Args:
            prompt: 图片生成提示词
            output_path: 输出文件路径

        Returns:
            生成的图片文件路径

        Raises:
            Exception: 生成失败时抛出异常
        """
        # 准备请求头
        headers = {
            "Content-Type": "application/json"
        }

        # 构建请求体
        payload = {
            "model": self.model,
            "prompt": prompt,
            "upload_img_config": self.upload_config
        }

        logger.info(f"发送请求到: {self.api_url}")
        logger.debug(f"Prompt 长度: {len(prompt)} 字符")

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=300  # 5分钟超时
            )
        except requests.exceptions.Timeout:
            raise Exception(
                "API 请求超时（300秒）。\n"
                "可能原因：\n"
                "1. 网络连接问题\n"
                "2. API 服务响应过慢\n"
                "建议：检查网络连接或重试"
            )
        except requests.exceptions.RequestException as e:
            raise Exception(
                f"API 请求失败: {str(e)}\n"
                "可能原因：\n"
                "1. 网络连接问题\n"
                "2. API 地址配置错误\n"
                "建议：检查网络连接和 API 配置"
            )

        # 检查 HTTP 状态码
        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(f"API 请求失败: status={response.status_code}, error={error_detail}")
            raise Exception(
                f"API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                "可能原因：\n"
                "1. API 服务端错误\n"
                "2. 请求参数不符合 API 要求\n"
                "建议：检查 API 配置和请求参数"
            )

        # 解析响应
        try:
            result = response.json()
        except json.JSONDecodeError:
            raise Exception(
                f"API 响应格式错误，无法解析为 JSON\n"
                f"响应内容: {response.text[:500]}"
            )

        # 检查错误码
        error_code = result.get("error_code", -1)
        if error_code != 0:
            error_msg = result.get("error_msg", "未知错误")
            raise Exception(
                f"API 返回错误: error_code={error_code}, error_msg={error_msg}"
            )

        # 提取图片 URL
        data_list = result.get("data", [])
        if not data_list:
            raise Exception("API 返回的数据列表为空")

        image_url = data_list[0]
        logger.info(f"获取到图片 URL: {image_url}")

        # 下载图片
        try:
            img_response = requests.get(image_url, timeout=60)
            img_response.raise_for_status()
            image_data = img_response.content
        except Exception as e:
            raise Exception(f"下载图片失败: {str(e)}")

        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 保存图片
        with open(output_path, 'wb') as f:
            f.write(image_data)

        logger.info(f"✅ 图片生成成功: {output_path} ({len(image_data)} bytes)")
        return output_path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="图片生成 API 调用工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础用法
  python generate_image.py \\
    --prompt "一只可爱的猫咪" \\
    --output "./output/cat.png"

  # 使用自定义 API 地址
  python generate_image.py \\
    --prompt "美丽的风景" \\
    --api-url "http://custom-api.com/generate" \\
    --output "./output/scene.png"
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
        "--prompt",
        required=True,
        help="图片生成提示词（必需）"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="输出文件路径（例如：./output/image.png）"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志"
    )

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # 创建生成器实例
        generator = ImageGenerator(
            api_url=args.api_url,
            model=args.model
        )

        # 生成图片
        output_path = generator.generate_image(
            prompt=args.prompt,
            output_path=args.output
        )

        # 输出结果
        print(json.dumps({
            "success": True,
            "output_path": output_path,
            "message": "图片生成成功"
        }, ensure_ascii=False))

    except Exception as e:
        logger.error(f"图片生成失败: {str(e)}")
        print(json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
