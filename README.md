# 拆书房 · 静态阅读站

纯 HTML/CSS/JS，无构建步骤。双击 `index.html`（file://）或在本目录运行 `python3 -m http.server` 都能用。

| 页面 | 作用 |
|---|---|
| `index.html` | 书库：首屏、即时搜索（书名/作者/标签/导读全文/推荐）、分类筛选标签、封面书格、每日推荐模块 |
| `book.html?b=<slug>` | 书籍详情：封面、书目信息（附来源）、标签页「简介 / 导读分析 / 目录」、开始/继续阅读 |
| `reader.html?b=<slug>&m=ebook\|guide#c=<章id>` | 翻页阅读器：桌面跨页、手机单页；支持滑动、方向键、点击页边、页码、目录跳转、字号，并记住阅读位置 |
| `recs.html` | 每日推荐归档（最新在前，按日期分组） |

## 目录结构
- `books/<slug>.json` + `.js`：书目信息和**按章精读**内容。`books/index.json` + `index.js` 是书目总表（由脚本生成）。
- `covers/`：**真实**封面（从书店/出版社网站下载，绝不使用 AI 生成）。`covers/rec/` 存放推荐书的封面。
- `ebooks/<slug>.json` + `.js` + `ebooks/<slug>/img/`：**私人全文**（用户自有电子书转换而来）。**不得公开发布**，见下文「公开版」。
- `recommendations/<YYYY>.json` + `.js`、`recommendations/index.js`：每日推荐。
- `tools/`：各类脚本（先执行一次 `cd tools && npm install`，用于安装 esbuild）。

## 书籍 JSON 字段
```
{ slug, title, author, intro, chapterCount,
  cover: "covers/x.jpg", coverSource: "<页面 URL>",
  categories: ["历史","社科"], tags: ["中国", ...],      // 分类标签由数据驱动生成
  edition: "...", meta: { "出版社": "...", "ISBN": "...", ... }, metaSources: ["<URL>", ...],
  chapters: [ { id, title, caption?, kind: "front"|"part"|"chapter"|"back", blocks: [...] } ] }
```
`meta` 只填写经可靠来源核实过的内容，并在 `metaSources` 里注明来源。拿不到真实封面时，就不写 `cover`，网站会显示文字排版的占位封面。

## 新增一本书
1. 精读内容（来自 Canvas TSX `.canvas.txt`）：`node tools/extract.mjs <file.canvas.txt> <slug> "作者"`（可加 `--mode=tabs|sections`）。重新提取时会保留 cover/categories/tags/meta 等字段。没有 canvas 的话，也可以按上面的格式手写 JSON。
2. 封面：从博客來等书店下载**真实**商品图放入 `covers/`（书店多为立体书影，可透视校正裁出正面，比例约 1:1.42，不得修改内容），再运行 `python3 tools/cover-thumb.py covers/<名>.jpg` 生成 `covers/thumb/` 缩略图。然后在 `books/<slug>.json` 里补充 `cover`、`coverThumb`、`coverSource`、`coverNote`，多册书可加 `volumes:[{label,cover,thumb,source}]`（详情页会显示分册图集），以及 `cover`、`coverSource`、`categories`、`tags`、`meta`、`metaSources`，把封面放进 `covers/`。
3. `node tools/build-catalog.mjs`：根据 JSON 重新生成 `books/<slug>.js` 和书目总表。书库排序见 `books/catalog-order.json`。
4. （可选，仅私人使用）全文：`python3 tools/convert-ebook.py <book.epub|.txt|.pdf> <slug>` 会写入 `ebooks/`。
   - epub：按 toc.ncx 分章，跳过封面、目录、版权页；不超过 `--max-img-kb`（默认 120）的图片保留，更大的丢弃。
   - txt：按「第X章 / 一、/ 序 / 后记 / 跋」切分（可在脚本中修改 `CH_RE`）；pdf 需要先安装 `pdftotext`（poppler-utils）。
   有 `ebooks/<slug>.js` 时，阅读器默认打开全文；没有时显示「按章精读版」，详情页也会如实标注。

## 每日推荐
```
node tools/add-rec.mjs --date 2026-10-25 --title "书名" --author "作者" --why "为什么推荐" \
  --tags 历史,社科 --cover covers/rec/书名.jpg --source https://book.douban.com/subject/... [--book <站内slug>]
```
- 封面必须是下载来的真实图片；不提供 `--cover` 时会显示占位封面。
- 按年份写入 `recommendations/<YYYY>.json/.js`；日期加书名相同时会覆盖原条目。首页和 `recs.html` 都会自动更新，内容也会进入搜索。

## 公开版（不含全文）
`sh tools/build-public.sh [输出目录]`（默认 `../reading-site-public`）：复制站点时排除 `ebooks/` 和 `shots/`，阅读器会自动回退为精读版。**只发布这个目录。**

## 密码保护版（可放 GitHub Pages）
`node tools/build-protected.mjs [输出目录] [--password <密码>] [--iter 310000]`（默认输出 `../reading-site-protected`）。
- 每本 `ebooks/<slug>.json`（图片内联为 data URI）用 AES-256-GCM 加密，密钥由 PBKDF2-SHA256（随机盐，默认 310000 次迭代）从密码派生，输出 `ebooks/<slug>.enc.js`；明文 ebooks 不会被复制。只有章节标题（目录）以明文存放。
- 不传 `--password` 时会随机生成密码，写入 `<输出目录>-PASSWORD.txt`（不进入站点）。
- 阅读器打开全文时会弹出密码框，在浏览器内用 WebCrypto 解密；勾选「记住此设备」后，派生出的密钥存入 localStorage，不勾选则只存在本次会话（sessionStorage）。首页、搜索、导读无需密码。
- 自动添加 `noindex` meta、`robots.txt`（Disallow: /）和 `.nojekyll`。把输出目录推送到 GitHub 仓库并开启 Pages 即可。
