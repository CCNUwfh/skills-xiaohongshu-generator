---
name: xiaohongshu-content-creator
description: 整合小红书大纲生成与图片生成，一键创建完整图文内容；当用户需要生成小红书笔记（大纲+配图）、批量创作图文内容时使用
dependency:
  python:
    - requests>=2.31.0
  system: []
---

# 小红书内容创建器

## 任务目标
- 本 Skill 用于: 整合大纲生成和图片生成两个功能，自动创建完整的小红书图文内容
- 能力包含:
  - 调用 LLM API 生成结构化的小红书内容大纲
  - 自动解析大纲中的页面内容
  - 为每个页面生成小红书风格配图
  - 保持所有图片风格一致
- 触发条件: 用户需要生成完整的小红书笔记（包含文字大纲和配套图片）

## 前置准备

### API 配置
本 Skill 使用预设配置，无需 API Key：

1. **大纲生成 API**（用于生成内容大纲）
   - 使用预设配置，无需 API Key
   - `api_url`: 默认 `http://ai-outside-service.smzdm.com:8000/ai-outside-model/v1/get_chat_data`
   - `model`: 默认 `gemini-3.1-pro-preview`
   - `source`: 默认 `ai_skill_all_weifuhe`

2. **图片生成 API**（用于生成配图）
   - 使用预设配置，无需 API Key
   - `api_url`: 默认 `http://openai-cv-service.smzdm.com:809/pictures/create_img`
   - `model`: 默认 `img_6_2_20251124_v3`

### 依赖说明
脚本所需的依赖包：
```
requests>=2.31.0
```

## 操作步骤

### 标准流程
1. **准备参数**
   - 确定内容主题
   - 确定生成页数（可选，默认5页）

2. **执行内容创建**
   - 调用 `scripts/create_content.py` 脚本
   - 传入主题参数
   - 指定输出目录（可选）

3. **自动处理流程**
   - 脚本自动调用大纲生成 API 创建结构化大纲
   - 解析大纲中的 `<page>` 标签，提取每个页面的内容和类型
   - 为每个页面调用图片生成 API 生成配图

4. **获取结果**
   - 大纲文件：`outline.md`
   - 图片文件：`page_01_封面.png`、`page_02_内容.png` 等
   - JSON 格式的执行结果报告

### 使用示例

**基础用法（使用默认配置，生成5页）：**
```bash
python scripts/create_content.py \
  --topic "新手如何学会手冲咖啡"
```

**指定页数和输出目录：**
```bash
python scripts/create_content.py \
  --topic "春日穿搭指南" \
  --pages 8 \
  --output-dir "./my-notes"
```

## 资源索引

### 必要脚本
- **[scripts/create_content.py](scripts/create_content.py)**
  - 用途：整合流程的主入口脚本
  - 参数：
    - `--topic`: 主题（必需）
    - `--pages`: 生成页数（默认：5页）
    - `--output-dir`: 输出目录（可选，默认 `./output`）

- **[scripts/generate_outline.py](scripts/generate_outline.py)**
  - 用途：生成小红书内容大纲
  - 参数：topic（必需）, pages（可选，默认5）, api_url（可选）, model（可选）, source（可选）

- **[scripts/generate_image.py](scripts/generate_image.py)**
  - 用途：生成小红书风格配图
  - 参数：prompt（必需）, output_path（必需）, api_url（可选）, model（可选）

### 领域参考
- **[references/outline-prompt.md](references/outline-prompt.md)**
  - 何时读取：了解大纲生成提示词模板和输出格式

- **[references/image_prompt_template.txt](references/image_prompt_template.txt)**
  - 何时读取：了解图片生成提示词模板和设计要求

## 注意事项

### API 配置
- 大纲生成和图片生成均使用预设配置，无需 API Key
- 所有参数都使用默认值，开箱即用
- 如需自定义，可以修改脚本中的默认配置或通过参数覆盖

### 输出格式
- 大纲文件使用 Markdown 格式，包含 `<page>` 标签分隔符
- 图片文件命名格式：`page_{序号}_{类型}.png`
- 页面类型包括：封面、内容、总结

### 风格一致性
- 图片生成使用统一的提示词模板
- 如果需要调整风格，可以修改 `references/image_prompt_template.txt`

### 错误处理
- 如果某个页面的图片生成失败，脚本会停止执行
- 检查 API 配置和网络连接
- 查看日志输出了解详细错误信息

## 技术细节

### 大纲解析
脚本使用正则表达式解析大纲内容，提取格式为：
```
[类型]
页面内容

<page>
```

### 图片生成顺序
1. 第一页（封面）- 无参考图片
2. 第二页开始 - 使用上一张图片作为参考，保持风格一致

### 输出目录结构
```
output/
├── outline.md              # 大纲文件
├── page_01_封面.png        # 封面图片
├── page_02_内容.png        # 内容页图片
├── page_03_内容.png        # 内容页图片
└── page_04_总结.png        # 总结页图片
```
