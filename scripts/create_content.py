#!/usr/bin/env python3
"""
小红书内容创建整合脚本
自动生成大纲并为每个页面生成图片
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_outline(outline_text: str) -> list:
    """
    解析大纲文本，提取每个页面的内容和类型

    Args:
        outline_text: 大纲文本

    Returns:
        页面列表，每个元素包含 type 和 content
    """
    pages = []

    # 使用正则表达式匹配 <page> 标签之间的内容
    # 格式：[类型]\n内容<page>
    pattern = r'\[([^\]]+)\]([^<]*?)(?=<page>|$)'
    matches = re.findall(pattern, outline_text, re.DOTALL)

    if not matches:
        raise Exception(
            "无法解析大纲内容。\n"
            "请确保大纲使用正确的格式：\n"
            "- 每页开头使用 [类型] 标记（如：[封面]、[内容]、[总结]）\n"
            "- 每页之间使用 <page> 标签分隔"
        )

    for i, (page_type, content) in enumerate(matches, 1):
        pages.append({
            "index": i,
            "type": page_type.strip(),
            "content": content.strip()
        })
        logger.info(f"解析页面 {i}: 类型={page_type.strip()}, 内容长度={len(content.strip())}, 预览={content.strip()[:100]}...")

    return pages


def generate_outline(topic: str, pages: int = 5) -> str:
    """
    调用 generate_outline.py 生成大纲

    Args:
        topic: 主题
        pages: 生成页数（默认5页）

    Returns:
        大纲文本
    """
    logger.info("=" * 60)
    logger.info("步骤 1: 生成小红书内容大纲")
    logger.info("=" * 60)
    logger.info(f"目标页数: {pages} 页")

    script_path = Path(__file__).parent / "generate_outline.py"

    if not script_path.exists():
        raise FileNotFoundError(f"脚本不存在: {script_path}")

    cmd = [
        sys.executable,
        str(script_path),
        "--topic", topic,
        "--pages", str(pages)
    ]

    logger.info(f"执行命令: {' '.join(cmd)} ...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10分钟超时
            check=True
        )
        outline = result.stdout.strip()

        if not outline:
            raise Exception("大纲生成失败：返回内容为空")

        logger.info(f"✅ 大纲生成成功，长度: {len(outline)} 字符")
        return outline

    except subprocess.TimeoutExpired:
        raise Exception("大纲生成超时（10分钟），请检查网络连接或稍后重试")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout
        raise Exception(f"大纲生成失败:\n{error_msg}")


def generate_image(
    page_content: str,
    page_type: str,
    output_path: str,
    full_outline: str,
    user_topic: str
) -> str:
    """
    调用 generate_image.py 生成图片

    Args:
        page_content: 页面内容
        page_type: 页面类型
        output_path: 输出路径
        full_outline: 完整大纲
        user_topic: 用户主题

    Returns:
        图片文件路径
    """
    # 构建 prompt（从模板文件读取）
    script_dir = Path(__file__).parent
    template_path = script_dir.parent / "references" / "image_prompt_template.txt"

    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        prompt = template.format(
            page_content=page_content,
            page_type=page_type,
            full_outline=full_outline,
            user_topic=user_topic if user_topic else "未提供"
        )
    else:
        # 如果模板文件不存在，使用简单格式
        prompt = f"{page_type}\n{page_content}"

    script_path = script_dir / "generate_image.py"

    if not script_path.exists():
        raise FileNotFoundError(f"脚本不存在: {script_path}")

    cmd = [
        sys.executable,
        str(script_path),
        "--prompt", prompt,
        "--output", output_path
    ]

    logger.info(f"执行命令: {' '.join(cmd[:4])} ...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10分钟超时
            check=True
        )

        # 解析输出
        output = result.stdout.strip()
        try:
            result_data = json.loads(output)
            if result_data.get("success"):
                return result_data.get("output_path")
            else:
                raise Exception(result_data.get("error", "未知错误"))
        except json.JSONDecodeError:
            # 如果输出不是JSON格式，假设路径是output_path
            return output_path

    except subprocess.TimeoutExpired:
        raise Exception(f"图片生成超时（10分钟），页面: {page_type}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout
        raise Exception(f"图片生成失败 (页面: {page_type}):\n{error_msg}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="小红书内容创建整合工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础用法
  python create_content.py \\
    --topic "新手如何学会手冲咖啡"

  # 指定页数和输出目录
  python create_content.py \\
    --topic "春日穿搭指南" \\
    --pages 8 \\
    --output-dir "./my-notes"
        """
    )

    # 内容参数
    parser.add_argument(
        "--topic",
        required=True,
        help="内容主题"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="生成页数（默认：5页）"
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="输出目录（默认：./output）"
    )

    args = parser.parse_args()

    try:
        logger.info(f"大纲主题为 {args.topic}")
        # 步骤 1: 生成大纲
        outline = generate_outline(
            topic=args.topic,
            pages=args.pages
        )

        # 保存大纲到文件
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        outline_file = output_dir / "outline.md"

        with open(outline_file, "w", encoding="utf-8") as f:
            f.write(outline)

        logger.info(f"✅ 大纲已保存到: {outline_file}")

        # 步骤 2: 解析大纲
        logger.info("")
        logger.info("=" * 60)
        logger.info("步骤 2: 解析大纲内容")
        logger.info("=" * 60)

        pages = parse_outline(outline)
        logger.info(f"✅ 解析完成，共 {len(pages)} 个页面")

        # 步骤 3: 生成图片
        logger.info("")
        logger.info("=" * 60)
        logger.info("步骤 3: 为每个页面生成图片")
        logger.info("=" * 60)

        generated_images = []
        reference_image = None  # 用于保持风格一致

        for i, page in enumerate(pages, 1):
            logger.info(f"第{i}页内容预览: {page['content'][:100]}...")
            logger.info(f"正在生成第 {i}/{len(pages)} 页图片...")
            logger.info(f"页面类型: {page['type']}")

            # 生成输出文件名
            output_filename = f"page_{i:02d}_{page['type']}.png"
            output_path = output_dir / output_filename

            # 生成图片
            image_path = generate_image(
                page_content=page['content'],
                page_type=page['type'],
                output_path=str(output_path),
                full_outline=outline,
                user_topic=args.topic
            )

            generated_images.append(image_path)
            logger.info(f"✅ 图片已保存: {image_path}")

        # 步骤 4: 输出总结
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 所有任务完成！")
        logger.info("=" * 60)
        logger.info(f"生成的图片数量: {len(generated_images)}")
        logger.info(f"输出目录: {output_dir.absolute()}")
        logger.info("")
        logger.info("生成的文件:")
        logger.info(f"  📄 大纲文件: {outline_file}")
        for img_path in generated_images:
            logger.info(f"  🖼️  {Path(img_path).name}")

        # 输出 JSON 格式结果
        print(json.dumps({
            "success": True,
            "topic": args.topic,
            "outline_file": str(outline_file),
            "output_dir": str(output_dir.absolute()),
            "pages_count": len(pages),
            "images": generated_images
        }, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}")
        print(json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
