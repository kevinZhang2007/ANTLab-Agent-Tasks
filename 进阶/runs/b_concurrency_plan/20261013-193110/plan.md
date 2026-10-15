# 进阶B：独立客户端、排队请求与独立进程验证计划

状态：`planned_not_run`。记录时间：2026-10-13T19:31:10.377978+08:00。代码基点：`78b97898e713a3b8ec2cdffeec8c6758c4bcbbc9`。

本轮只审查源码并保存计划。以下启动、HTTP请求、并发发送及清理命令均未执行，没有通过结果，不新增模型调用。

## 1. 已核对的实现

- `进阶/challenge_b/server_review.py`第9、120—122行使用标准`HTTPServer`，不是线程或多进程服务；一个进程串行处理请求。客户端同时发送时可能在连接或请求队列等待，不能据此验证Engine并发执行安全。
- 第112—114行在进程启动时加载一次固定资料并创建一个全局Engine。第87—90行任何客户端的`reset=true`均清空该进程共享Engine的cache，然后执行本次请求。没有每客户端Engine或用户会话隔离。
- 第18—21、92—96行将完整输入、cache前后、响应及request_id写入该进程的`events.jsonl`。日志没有客户端身份和处理开始/结束区间，不能仅靠完成日志证明执行重叠。
- 第106—111、115—120行允许指定Engine、端口与新日志目录，只绑定127.0.0.1；已有日志目录会拒绝启动。没有认证、授权、用户ID、负载均衡或worker管理，也没有跨进程缓存/IPC配置。
- `no_cache_engine.py`保留空cache以兼容reset，evaluate不读写它；原Engine按query缓存。新开两个服务进程按源码应各有一个独立Engine，本计划将核对这种状态独立性，不称为托管多worker验证。

源码SHA-256：

| 文件 | SHA-256 |
|---|---|
| server_review.py | ee1a5bc3d573c3279075d479b88fb4d348b5b788c8e9a0482bd8d78eee33075b |
| challenge.py | b84a035957ac457fb803c82f141c8684ccb5dbe9ff34c45bbb199ff613094ad1 |
| no_cache_engine.py | ab5852c20284e4f17097a1a9d7ac5343cf9dfea107e0f430c5ccda253f38d87a |
| data.json | f3ba571d72e2836221ed3026ac764d8e0da569fc5b8bd895f702cbd2896296a4 |

独立客户端测试不等于用户权限隔离验证。客户端A/B只是测试端标识，不是系统已有用户身份。

## 2. 启动命令（尚未执行）

从仓库根目录准备以下变量；每条服务命令在独立PowerShell会话执行，各会话都先设置同样变量。每阶段最多两个服务，原版阶段停止后再进行修复版阶段。

```powershell
$projectRepo = 'C:\Users\86186\Projects\ANTLab-Agent-Tasks'
$testPython = 'C:\Users\86186\AppData\Local\Programs\Python\Python314\python.exe'
$trialRoot = "$projectRepo\进阶\runs\b_concurrency_execution\20261013-193110"

# 原版阶段：两个独立服务进程
& $testPython -X utf8 -B "$projectRepo\进阶\challenge_b\server_review.py" --port 8896 --engine challenge:Engine --log-dir "$trialRoot\original-p1"
& $testPython -X utf8 -B "$projectRepo\进阶\challenge_b\server_review.py" --port 8897 --engine challenge:Engine --log-dir "$trialRoot\original-p2"

# 原版两个进程停止后，修复版阶段
& $testPython -X utf8 -B "$projectRepo\进阶\challenge_b\server_review.py" --port 8898 --engine no_cache_engine:Engine --log-dir "$trialRoot\fixed-p1"
& $testPython -X utf8 -B "$projectRepo\进阶\challenge_b\server_review.py" --port 8899 --engine no_cache_engine:Engine --log-dir "$trialRoot\fixed-p2"
```

开始前确认这四个端口没有其他监听服务，不结束其他程序。日志目录必须不存在；若存在，停止检查并另登记新执行目录，不清空旧目录。记录自己启动的PID、实际命令、端口、日志目录和startup事件。读取`/api/cases`核对服务版本、Engine选择和哈希，资料须与本计划一致。

## 3. 固定输入与客户端

HTTP接口为`POST /api/run`，Content-Type为`application/json`。仅使用原题包R01、R02，避免将beta已知漏证混进状态隔离判断。固定query均为`timeout request threshold`，doc_ids均为`["alpha"]`，k=2，mode为`offline_replay`。

R01正文：

```json
{"case_id":"R01","reset":false,"request":{"query":"timeout request threshold","doc_ids":["alpha"],"snapshot":"v1","k":2,"mode":"offline_replay"}}
```

R02正文：

```json
{"case_id":"R02","reset":false,"request":{"query":"timeout request threshold","doc_ids":["alpha"],"snapshot":"v2","k":2,"mode":"offline_replay"}}
```

序列中的reset请求只将对应正文的reset改为true。服务仍使用data.json的固定draft，不编辑答案或引用。单次手动请求写法如下（未执行）：

```powershell
$body = '{"case_id":"R01","reset":true,"request":{"query":"timeout request threshold","doc_ids":["alpha"],"snapshot":"v1","k":2,"mode":"offline_replay"}}'
Invoke-WebRequest -Uri 'http://127.0.0.1:8896/api/run' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 10
```

正式执行计划时，需先准备独立测试驱动：A/B各自使用独立HTTP客户端及连接，客户端标识、attempt编号保存在测试记录，不伪装成服务认证。非并发序列必须等待上一响应保存后继续；并发组使用同一测试进程内两个线程、两个独立urllib opener及Barrier同时释放发送，不使用共享响应变量。驱动仅发送固定离线请求，记录原始正文与响应，不修补输出。本轮不实现或运行驱动。

## 4. 四组输入序列与预期

每组分别运行原版与修复版，使用P1；第三组同时使用P1/P2。每组以显式reset开始，保持其余输入和代码不变。预期来自源码，不是已观测结果。

| 组 | 固定执行顺序 | 预测与断言 |
|---|---|---|
| 独立客户端交错 | A→P1 R01/reset；B→P1 R02；A→P1 R01；B→P1 R02 | 原版预计B取到旧v1/b01；修复版A取b01/v1、B取b02/v2。每次request回显对应本次正文，request_id不重复。原版污染作为预期失败保留，不算隔离通过。 |
| 客户端并发发送 | 先A→P1 R01/reset并保存；随后A发送R01、B发送R02，由Barrier同时释放 | 原版预计两项均使用已预热v1缓存；修复版分别返回v1/b01和v2/b02。两个响应ID不得相同或错配。不能假定服务接收先后，按响应ID关联日志；HTTPServer串行，结果只评价排队与响应隔离。 |
| 独立服务进程 | A→P1 R01/reset；B→P2 R02/reset；A→P1 R02；B→P2 R01；B→P2 R01/reset；A→P1 R02 | 原版预计P1保留v1缓存、P2最初保留v2缓存；P2 reset后不清P1，最后P1仍复用其旧v1。修复版每次按当次范围处理。检查P1/P2的startup、Engine、日志归属不同，不能从修复版cache始终为空单独证明隔离；原版状态探针是正对照。 |
| 跨客户端reset交错 | A→P1 R01/reset；B→P1 R02；A→P1 R02/reset；B→P1 R01 | 原版预计B第一项复用v1，A reset后cache变为v2，B最后取旧v2。这说明同进程reset影响其他客户端；不是用户隔离通过。修复版分别按v1/v2返回，reset清空的是共享但未使用的空cache。确定序列等待上一响应完成，不声称测试了reset竞态。 |

计划直接HTTP请求总数为34：每版4+3+6+4=17项，含预热、reset和原版预期失败。并发发送组每版只两个同时发送请求，不增加压力轮次。技术失败后未执行项单列；不得补跑、挑结果或自动重试。本计划不新增页面或模型调用。

## 5. 断言与日志关联

每次保存客户端标签、attempt编号、目标端口、请求发送与接收时间、完整HTTP正文、HTTP状态和原始响应。客户端完整HTTP耗时与Engine.elapsed_ms分开；均属offline_replay，不与基础模型耗时比较。

按响应request_id查对应进程events.jsonl，要求恰好一条请求日志；核对http_body、engine_request、完整corpus、固定draft来源、cache_before/cache_after、service.engine及engine_sha256，与本次响应逐项一致。另记录客户端attempt→request_id→PID/端口→日志行号的索引。不能靠query关联，因为本计划故意使用相同query。

分别核对原Engine响应和外层展示映射：

- 修复版实际证据id/doc_id/snapshot/text/page与本次资料一致，不接受空证据作为本组成功；R01对应b01，R02对应b02。原版预期污染保留完整实际证据和范围冲突。
- request_id在全部实际请求中唯一；响应request回显与该客户端正文一致，不使用共享的“最后响应”。
- 外层support_status始终not_checked，judgment_source为unverified；Engine原始supported不当作语义金标准。外层locator结合实际范围核对，不能将越界旧证据标valid。
- 重置前后缓存由日志直接核对；跨进程对照看各自日志和响应，不假定共享缓存。日志缺失、重复ID、错配或损坏都保留并停止，不自动修补。
- 成功返回、范围隔离、定位、语义未核验和状态共享分别报告，不能只凭HTTP200判通过。不评价用户授权，因为没有用户身份机制。

## 6. 停止与清理

任何源码/资料哈希变化、Engine选择不符、端口占用、服务加载失败、HTTP非200、连接错误或10秒超时：保存错误和已完成数量后停止。先检查日志判断失败请求是否已执行，不自动重发。原版预期缓存污染及共享reset是质量结果，保存后继续既定序列；修复版范围错配、ID/日志错配则保存后停止。

每阶段完成或停止后，在自己启动的两个服务终端按Ctrl+C；检查该阶段端口不再监听，并登记进程退出及日志shutdown事件是否存在。只停止本次明确登记的进程；无法确认归属时不结束进程，报告阻塞。不删除执行目录、失败、旧日志或截图。最终停止两个阶段全部自有服务，再只读核对原代码、基础冻结材料和旧记录哈希。

## 7. 当前缺项与适用边界

- 本计划为planned_not_run；尚无这34项结果、并发客户端驱动、执行日志、计时或通过结论。
- 独立客户端没有认证身份，不等于用户权限隔离。一个全局Engine与reset影响所有客户端是源码可见的共享状态；无权限契约可据此证明安全。
- 标准HTTPServer串行处理，无法验证Engine线程安全、同时执行reset/evaluate的竞态、并发日志写入安全或请求取消。要研究这些需另行授权与独立方案，不能悄悄切换服务类型。
- 两个端口上的独立服务进程不等于已有worker管理；未覆盖负载均衡、共享缓存/数据库、多worker一致性、故障恢复或真实生产负载。
- top-k漏证、Engine语义误标和未知范围固定draft/status=ok限制保持原样。此计划不修复这些问题。
- 没有用户权限隔离、真正并发执行安全和托管多worker结果；不得把既有单进程离线修复扩大为整个系统安全或完整正确。
