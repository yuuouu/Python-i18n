---
dg-publish: true
title: Python‑i18n 多端翻译文件生成器
dg-path: 业务思考/Python‑i18n 多端翻译文件生成器
dg-created: 2025-09-13
---
> [!summary] AI摘要
>本项目 Python-i18n (PyI18nX) 是一个用 Python 编写的多语言资源生成工具。它可以读取包含 key 和多语言翻译的 Excel 表格，自动检测 key 列，跳过空行并忽略注释列，对缺失翻译内容回退到英文。脚本会一次性生成 Android 的 strings.xml、iOS 的 Localizable.strings 以及 PC 的 .ini 文件。通过统一翻译入口，避免手动维护差异，支持多语种扩展，实现从 Excel 到多端翻译文件的一键自动化生成。

>[https://github.com/yuuouu/Python-i18n](https://github.com/yuuouu/Python-i18n)
## 介绍

`Python‑i18n` 是一个多端翻译文件生成器，用于将产品团队维护的 Excel 多语言表格转换为各端（Android、iOS、PC）所需的翻译文件。通过统一翻译源表和输出标准，避免各端手动拷贝时产生偏差。  

该项目包含以下内容：

- **i18n_converter.py**：主要的转换脚本。读取 `.xlsx` 格式的翻译表，根据指定的目标平台（android,ios,pc）生成对应的资源文件并输出到 `res` 目录。
- **sample.xlsx**：示例翻译表。表格必须包含一列名为 `key`的唯一标识，其余各列代表不同的语言。列名中的**括号部分视为语言代码**。例如 `中文(zh‑CN)` 会被解析为语言代码 `zh‑CN`。如果没有括号，则整列名作为语言代码使用。 脚本会将`key`左侧的列当成注释，只识别右侧的列。
- **res**：多语言输出目录
## 使用方法

1. 准备好你的翻译 Excel 文件。
2. 安装依赖。脚本基于 [pandas](https://pandas.pydata.org/) 和 Python 标准库：

```bash
pip install pandas openpyxl
```

3. 执行脚本。例如转换示例文件到所有平台：

```bash
python3 i18n_converter.py --input sample.xlsx --output res --platforms android,ios,pc
```

   参数说明：

   - `--input` / `-i`：必需。要转换的 `.xlsx` 文件路径。
   - `--output` / `-o`：输出目录的根目录，默认为 `res`。脚本会在该目录下创建对应平台所需的子目录。
   - `--platforms` / `-p`：逗号分隔的平台列表，支持 `android`、`ios` 和 `pc`。默认同时生成三端文件，参数为：`defautlPlatform`。

4. 输出结果：

   - **Android**：会在 `res/values-<语言代码>/strings.xml` 中生成 `<string name="key">value</string>`。
   - **iOS**：生成 `res/<语言代码>.lproj/Localizable.strings` 文件。格式为 `"key" = "value";`，编码为 UTF‑8。
   - **PC**：生成 `res/<语言代码>.ini` 文件。格式为 `key = "value";`。

5. 重复 Key 检测：脚本会检查 `key` 列是否有重复。若存在重复项，将打印错误并中止输出，以便修复表格后重新执行。

## 示例

clone本项目后，在项目目录中运行以下命令生成翻译文件：

```bash
python3 i18n_converter.py --input sample.xlsx --output res --platforms android,ios,pc
```

生成的目录结构如下：

```
res/
├── values-es/
│   └── strings.xml
├── values-zh-CN/
│   └── strings.xml
├── values-zh-TW/
│   └── strings.xml
├── es.lproj/
│   └── Localizable.strings
├── zh-CN.lproj/
│   └── Localizable.strings
├── zh-TW.lproj/
│   └── Localizable.strings
├── es.ini
├── zh-CN.ini
└── zh-TW.ini
```

你可以根据实际的列名扩展支持更多语言，只需保证列名括号内包含正确的语言代码。注意，多语言列中，**英语列(es)内容不允许空**，在其它列内容为空的情况下默认使用英语列内容。

## 高阶用法

如果你使用[Listary](https://www.listary.com/)软件，那么在`选项`-`命令`中添加一条命令。
在唤起Listary之后，输入关键字`fy`，按回车即可静默完成翻译工作，`--o "项目\res"`可将生成文件直接写入到项目中，一步到位！

![高阶用法](http://upforme.ru/uploads/001c/43/d3/2/865670.png)

```
/k python3 "D:\python-i18n\i18n_converter.py"  --input "D:\python-i18n\sample.xlsx" --platforms android --o "D:\code\project\model\src\main\res"
```


> 语言代码表：[http://www.lingoes.net/zh/translator/langcode.htm](http://www.lingoes.net/zh/translator/langcode.htm)