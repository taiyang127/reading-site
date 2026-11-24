# 乾隆《泉州府志》原文 · 译文 · 注解

本目录由脚本根据译文源稿自动生成，请勿手工改这里的 HTML。

## 增加新卷后如何更新

把新的 Markdown（文件名形如 `54-卷五十四-文苑.md`）放到源目录，然后在站点根目录执行：

```bash
python3 tools/build-fuzhi-yizhu.py
```

默认读取 `/workspace/fuzhi-translation/`，输出到本目录。也可指定路径：

```bash
python3 tools/build-fuzhi-yizhu.py --src /path/to/fuzhi-translation --out fuzhi
```

- 门类：`tools/fuzhi-categories.json`。已有卷用编号指定；新卷按标题关键词归类，匹配不到则进入「其他」。
- 文件名 `75上-…md`、`75下-…md` 分别生成 `v/75a.html`、`v/75b.html`，排在卷七十四与卷七十六之间。
- 人名 / 地名索引：由篇目标题自动抽名，再通检全书。停用词、手工别称见 `tools/fuzhi-entities.json`（如 `蔡襄` ↔ `蔡忠惠`）。脚本也会从本传里的「字」「号」「谥」补别称。改完配置后同样再跑一遍上面的命令。

源稿体例：卷题与说明之后，按「**原文** / **译文** / **注解**」对写。列传等卷若译文按人分条（`### 人名`），或卷末用 `## 注解`，脚本均可识别。正文只做排版，不改字。
