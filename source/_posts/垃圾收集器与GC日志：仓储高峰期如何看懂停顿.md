---
title: 垃圾收集器与GC日志：仓储高峰期如何看懂停顿
date: 2023-06-18 10:00:00
tags: [Java, JVM, GC日志, G1, 供应链系统]
---

GC 日志是 JVM 调优和线上排查的第一手证据。接口变慢时，不能只看业务日志里的耗时，还要判断是否发生了 Stop The World、Full GC、老年代空间不足、晋升失败或大对象分配。供应链系统在大促、仓库波次下发、订单集中履约时对象创建速度很快，GC 日志能帮助我们把问题从“感觉慢”变成可量化的事实。

## 整体流程图

![GC 日志分析流程](/images/tech-flowcharts/gc-log-analysis-flow.svg)

## 常见垃圾收集器

不同 JDK 版本和业务场景会使用不同收集器：

1. Serial GC：单线程收集，适合小内存客户端程序，不适合高并发服务。
2. Parallel GC：吞吐优先，适合批处理任务，例如夜间库存重算、历史订单归档。
3. CMS：低停顿老年代收集器，JDK 9 后被标记废弃，JDK 14 移除。
4. G1：面向服务端低停顿场景，JDK 9 以后成为默认收集器，适合大多数订单、库存、仓储服务。
5. ZGC：低停顿收集器，适合大堆和低延迟服务，具体使用要结合 JDK 版本和生产验证。

如果没有特殊原因，现代 Spring Boot 服务通常优先使用 G1。它把堆划分为多个 Region，通过预测停顿时间选择回收集合，目标是在可控停顿下获得稳定吞吐。

## 仓储高峰期 Demo

假设 WMS 在晚上 8 点下发波次任务，订单服务要把 30 万个待出库订单按仓库、承运商、优先级分组：

```java
public class WaveDispatchService {
    public List<WaveGroup> buildWave(List<OrderLine> lines) {
        Map<String, List<OrderLine>> grouped = lines.stream()
                .collect(Collectors.groupingBy(line ->
                        line.getWarehouseCode() + ":" + line.getCarrierCode()));

        return grouped.entrySet().stream()
                .map(entry -> new WaveGroup(entry.getKey(), entry.getValue()))
                .collect(Collectors.toList());
    }
}
```

这段代码业务上清晰，但在高峰期会创建大量临时对象：分组 key、Map 节点、List、Stream 中间对象、`WaveGroup`。如果堆空间偏小或对象晋升过快，GC 停顿会明显增加。

## 如何打开 GC 日志

JDK 8 常用参数：

```bash
-XX:+PrintGCDetails \
-XX:+PrintGCDateStamps \
-XX:+PrintTenuringDistribution \
-Xloggc:/data/logs/order-service/gc.log
```

JDK 9 及以后推荐使用统一日志：

```bash
-Xlog:gc*,safepoint:file=/data/logs/order-service/gc.log:time,uptime,level,tags:filecount=10,filesize=100M
```

线上服务建议默认开启 GC 日志。日志文件滚动要配置好，否则长时间运行可能撑爆磁盘。

## GC 日志重点看什么

分析 GC 日志时，不要只看有没有 GC，要看四类指标：

1. 频率：Young GC、Mixed GC、Full GC 多久发生一次。
2. 停顿时间：每次暂停多少毫秒，P95/P99 是否影响接口 SLA。
3. 回收效果：GC 前后堆、老年代、元空间占用下降多少。
4. 触发原因：Allocation Failure、Metadata GC Threshold、Humongous Allocation、System.gc() 等。

一段简化后的日志可能类似：

```text
[2023-06-18T20:01:12.345+0800][info][gc] GC(42) Pause Young (Normal) 512M->180M(1024M) 35.7ms
[2023-06-18T20:03:44.210+0800][info][gc] GC(43) Pause Young (Concurrent Start) 760M->420M(1024M) 68.4ms
[2023-06-18T20:03:44.281+0800][info][gc] GC(44) Concurrent Mark Cycle
```

这说明 JVM 正在进行新生代回收，并启动并发标记。如果后面频繁出现 Full GC，且每次回收后老年代下降不明显，就要怀疑长生命周期对象过多或内存泄漏。

## 常见判断结论

GC 日志可以帮助形成明确结论：

1. Young GC 频繁但停顿短：对象创建速度快，可能需要优化批处理对象分配，或者适当增大堆。
2. Full GC 频繁且回收效果差：老年代长期占满，优先查缓存、静态集合、批量任务和大对象。
3. 元空间触发 GC：检查动态代理、脚本引擎、热部署和类加载器泄漏。
4. 大对象触发回收：检查一次性大数组、大 JSON、大 Excel 导出。
5. 明确出现 `System.gc()`：检查代码、第三方库或运维脚本是否主动触发 Full GC。

## 优化仓储波次的代码思路

对于前面的分组逻辑，可以从业务和代码两侧降压：

```java
public void dispatchWaveByPage(String waveNo) {
    long lastId = 0L;
    while (true) {
        List<OrderLine> page = orderLineRepository.queryPage(waveNo, lastId, 2000);
        if (page.isEmpty()) {
            break;
        }

        Map<RouteKey, List<OrderLine>> grouped = groupByRoute(page);
        waveRepository.saveGroups(grouped);
        lastId = page.get(page.size() - 1).getId();

        grouped.clear();
        page.clear();
    }
}
```

核心不是手动调用 GC，而是控制对象峰值：分页查询、分批落库、避免超大集合、减少无意义字符串拼接。GC 调优优先解决对象生命周期和分配速率，再调整 JVM 参数。

GC 日志的价值在于把性能问题证据化。对于供应链系统，订单高峰、仓储波次、库存同步都可能制造对象洪峰，只有把日志、业务峰值和代码路径结合起来看，才能得出可靠结论。
