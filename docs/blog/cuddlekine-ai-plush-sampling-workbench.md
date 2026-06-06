# CuddleKine: 用 AI 做毛绒玩具样品设计工作台

我最近在做一个叫 **CuddleKine** 的桌面应用，它的目标很明确：帮助毛绒玩具设计师把客户参考图、聊天记录和文字需求，整理成可生成、可修版、可交付给客户和工厂的样品资料。

传统的毛绒玩具打样流程里，设计师通常要反复整理客户需求、对照参考图、生成主视觉、补三视图、再整理给工厂看的生产资料。CuddleKine 想把这些环节放到一个连续的设计工作台里。

![CuddleKine home](../screenshots/01-cuddlekine-home.png)

## 它解决什么问题

CuddleKine 不是一个单纯的图片生成工具。它更像一个围绕毛绒玩具打样流程设计的 AI 工作台：

- 管理每个客户订单
- 上传参考图、照片、手绘图、聊天截图和文字素材
- 用 AI 整理结构化 brief
- 让设计师确认真正要进入生成流程的信息
- 生成毛绒玩具主图
- 生成正面、侧面、背面三视图
- 对单个视角进行画笔蒙版局部修版
- 导出客户确认图
- 导出工厂生产 PDF 和资料包

![Project library](../screenshots/02-project-library.png)

## 设计师先确认 brief

我不希望 AI 直接替设计师做所有判断。客户早期给的信息往往不完整，比如尺寸、用料、细节比例都可能还没确定。所以 CuddleKine 会先把素材整理成 brief，再让设计师决定哪些信息要保留、哪些信息暂时空着。

如果字段没有填写，后续导出的工厂 PDF 也不会硬塞空内容。这样早期初稿可以保持轻量，等客户确认后再补齐生产细节。

![Brief workbench](../screenshots/03-brief-workbench.png)

## 多模型接入

CuddleKine 支持多个生成服务：

- 本地 ComfyUI
- OpenAI 图像模型
- Agnes
- Replicate

每个模型的能力和风格都不一样，所以我把它做成可配置的 provider。用户可以在设置里填自己的 API Key，并选择适合自己项目的模型。

## 生成页是核心

生成工作台目前分成四个阶段：

1. 主图候选
2. 主图修版
3. 工厂三视图
4. 交付输出

设计师确认主图后，再生成正面、侧面、背面。三视图中的任意一个视角如果有问题，可以用画笔涂出要修改的位置，只重生成那一张，不影响另外两个视角。

![Generation workbench](../screenshots/04-generation-workbench.png)

## 客户和工厂看到不同资料

我把导出分成两类：

- 给客户：主图 + 三视图确认图
- 给工厂：生产 PDF + 原始图片 + brief JSON + metadata

这样客户看到的是干净的确认资料，工厂拿到的是更完整的生产参考。

## 技术栈

CuddleKine 当前使用：

- React 19 + Vite + TypeScript
- Tauri 2
- FastAPI
- SQLite / SQLAlchemy
- Pillow 图像处理
- ComfyUI workflow
- OpenAI / Agnes / Replicate API provider

## 下一步

接下来我想继续加强三件事：

- 提高三视图之间的一致性检查
- 增加工厂材料和工艺模板
- 做更精细的模型成本与质量评估

CuddleKine 现在已经从一个生图工具，逐渐变成一个面向毛绒玩具行业的 AI 应用工程项目。它不是为了替代设计师，而是让设计师更快地把想法变成可以沟通、可以修版、可以交付的样品资料。
