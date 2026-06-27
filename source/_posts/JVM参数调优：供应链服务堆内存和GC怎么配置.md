---
title: JVM参数调优：供应链服务堆内存和GC怎么配置
date: 2023-06-23 10:10:00
tags: [Java, JVM调优, JVM参数, GC, 供应链系统]
---

JVM 调优不是把网上的参数复制到生产环境。真正的调优要从业务目标出发：接口延迟、吞吐量、内存成本、GC 停顿、故障恢复速度。供应链服务通常既有在线接口，也有批处理任务，二者对 JVM 参数的要求不同，不能使用同一套配置机械套用。

## 整体流程图

![JVM 参数调优流程](/images/tech-flowcharts/jvm-tuning-parameters-flow.svg)

## 调优前先明确目标

调 JVM 参数之前，至少要回答四个问题：

1. 服务类型是什么：在线订单接口、库存查询、仓储波次、报表导出、定时批处理。
2. 核心指标是什么：P99 延迟、吞吐量、任务完成时间、内存占用、稳定性。
3. 当前瓶颈在哪里：GC 停顿、CPU、数据库、网络、锁竞争、对象分配过快。
4. 有哪些证据：GC 日志、堆 dump、线程 dump、监控曲线、压测报告。

没有证据的调优很容易变成参数玄学。JVM 参数只能解决 JVM 层面的问题，不能替代 SQL 优化、缓存设计、批处理拆分和业务限流。

## 常用参数分类

堆内存相关：

```bash
-Xms2g
-Xmx2g
-XX:NewRatio=2
-XX:MaxMetaspaceSize=512m
```

GC 相关：

```bash
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:InitiatingHeapOccupancyPercent=45
```

线程栈和直接内存：

```bash
-Xss512k
-XX:MaxDirectMemorySize=512m
```

诊断相关：

```bash
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/data/dump
-Xlog:gc*,safepoint:file=/data/logs/app/gc.log:time,uptime,level,tags:filecount=10,filesize=100M
```

容器相关要关注 JVM 对 cgroup 的识别能力。JDK 8 早期版本和 JDK 10 以后的行为不同，生产环境要确认基础镜像和 JDK 版本。

## 在线订单服务配置示例

在线订单服务关注接口延迟和稳定性。可以采用固定堆大小，减少运行时扩缩容带来的抖动：

```bash
JAVA_OPTS="
-Xms2g
-Xmx2g
-Xss512k
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:InitiatingHeapOccupancyPercent=40
-XX:MaxMetaspaceSize=512m
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/data/dump/order-service
-Xlog:gc*,safepoint:file=/data/logs/order-service/gc.log:time,uptime,level,tags:filecount=10,filesize=100M
"
```

这个配置适合中等规模的 Spring Boot 服务起步使用。实际值要根据容器内存、对象分配速率、流量峰值和压测结果调整。例如容器限制 3Gi 内存时，不能把 `-Xmx` 设置成 3g，因为元空间、线程栈、直接内存、JIT、JNI、系统开销也需要内存。

## 批处理服务配置示例

库存重算、订单归档、对账导出更关注吞吐和任务完成时间。批处理服务可以接受较长 GC 停顿，但要避免内存峰值导致 OOM：

```bash
JAVA_OPTS="
-Xms4g
-Xmx4g
-XX:+UseG1GC
-XX:MaxGCPauseMillis=500
-XX:ParallelGCThreads=4
-XX:ConcGCThreads=2
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/data/dump/reconcile-job
-Xlog:gc*:file=/data/logs/reconcile-job/gc.log:time,uptime,level,tags:filecount=5,filesize=200M
"
```

但批处理的第一优化点仍然是分批。下面这种一次性加载全量库存的写法不适合生产：

```java
public void rebuildInventorySnapshot() {
    List<InventoryRecord> all = inventoryRepository.findAll();
    List<InventorySnapshot> snapshots = all.stream()
            .map(this::toSnapshot)
            .collect(Collectors.toList());
    snapshotRepository.batchSave(snapshots);
}
```

更合理的是按主键或时间窗口拆分：

```java
public void rebuildInventorySnapshot() {
    long lastId = 0L;
    while (true) {
        List<InventoryRecord> page = inventoryRepository.findPage(lastId, 5000);
        if (page.isEmpty()) {
            break;
        }
        List<InventorySnapshot> snapshots = page.stream()
                .map(this::toSnapshot)
                .collect(Collectors.toList());
        snapshotRepository.batchSave(snapshots);
        lastId = page.get(page.size() - 1).getId();
    }
}
```

参数调优和代码优化要配合。否则即使堆从 2g 调到 8g，也只是延后 OOM 或把 Full GC 停顿变得更长。

## G1 调优注意事项

G1 常用调优思路：

1. 先设置合理的 `-Xms` 和 `-Xmx`，生产服务通常设置为相同值。
2. 通过 `MaxGCPauseMillis` 给 JVM 一个目标，但它不是强制保证。
3. 如果老年代增长过快，可以适当降低 `InitiatingHeapOccupancyPercent`，让并发标记更早开始。
4. 注意 Humongous Object，大对象会占用连续 Region，可能引发额外回收压力。
5. 不要轻易手动设置过多 G1 细节参数，先用 GC 日志验证问题。

## 调优闭环

一次合格的 JVM 调优应该形成闭环：

1. 记录问题：接口 P99 从 200ms 上升到 2s，GC 停顿明显增加。
2. 收集证据：GC 日志、堆使用曲线、对象分配热点、线程 dump。
3. 提出假设：订单波次分组产生大量临时对象，新生代回收频繁。
4. 小步调整：分页处理、降低对象峰值、调整堆大小或 G1 触发阈值。
5. 压测验证：对比吞吐、延迟、GC 次数、停顿时间。
6. 灰度发布：观察真实流量下的指标。

JVM 参数不是越多越专业。供应链系统的关键是把业务峰值、对象生命周期和 JVM 证据连起来，用最少的参数解决明确的问题。
