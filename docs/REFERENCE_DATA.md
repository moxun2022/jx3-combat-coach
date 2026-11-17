# 基础数据参考审阅

2026-11-17 审阅 https://github.com/Akatsuki-kurumi/jx3-death-review ，固定提交 ae60146c5dc799a310a0842fca619b833f750261。

## 可参考的数据结构

| 文件 | 用途 | 接入约束 |
| --- | --- | --- |
| data/buff-reference.json | 1381 个 Buff ID、1432 组 ID + 等级的监控标签 | 按客户端、版本、Buff ID、等级精确查询；等级 0 不自动匹配全部等级 |
| data/kill-analysis/buff-details-std.json | Buff 名称、描述、来源 URL 与获取时间 | 展示资料与机制证据分离，保留来源和时间 |
| data/kill-analysis/buff-semantic-overrides.json | 控制标签排除、精确等级的语义修正 | 作者规则是候选语义；不可直接作为已验证控制效果 |
| data/kill-analysis/roles.json | 引用 JX3BOX mount_group 的心法分组 | 核对目标版本，未知心法保留未知 |
| data/ai/game-facts-policy.json | 客户端与资料维护版本隔离 | std-2026-10-30 是维护标识，不推测成官方版本 |
| lib/jcl/kungfu.cjs | 心法名称批量查询与缓存 | 可借鉴缺失回退、查询失败保留未知、来源追踪 |

## 来源边界

上游声明代码 MIT，但 THIRD_PARTY_NOTICES.md 和 README 明确指出第三方 Buff 字典原作者及再分发许可未确认。当前项目不打包该字典，不导入冷却或技能机制常量。

Buff 监控标签并非官方机制；例如免控类标签不能仅按包含“控”判断为受到控制。上游描述的维护版本与监控声明日期亦需分别保留。当前只是审阅与接入设计，尚未将上游 ID 作为规则引擎事实。

后续独立建立 BuffReference（区别于 SkillSemantics），保留 client、game_version、buff_id、level、原标签、来源提交/文件/校验值、验证状态。显式导入用户提供的配置，经过脱敏日志和受控场景核对后再启用机制规则。
