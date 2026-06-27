---
title: JVM线上排查：FullGC、OOM和CPU飙高怎么定位
date: 2023-06-28 10:20:00
tags: [Java, JVM, OOM, FullGC, 线上排查, 供应链系统]
---

JVM 知识最终要落到线上排查。供应链系统通常链路长、依赖多、峰值明显，一次订单高峰可能同时触发接口变慢、消息堆积、GC 频繁、CPU 飙高。排查时不能只看某一个指标，而要把 JVM、业务流量、线程、内存和日志串起来。

## 整体流程图

![JVM 线上排查流程](/images/tech-flowcharts/jvm-troubleshooting-flow.svg)

## 必须掌握的工具

常用 JVM 排查工具包括：

1. `jps`：查看 Java 进程。
2. `jstat`：查看 GC、类加载、编译等统计。
3. `jstack`：导出线程栈，定位死锁、阻塞、CPU 高。
4. `jmap`：查看堆概要、导出 heap dump。
5. `jcmd`：JDK 7 以后推荐的综合诊断工具。
6. JFR：低开销运行时事件记录，适合分析 CPU、锁、IO、GC。
7. Arthas：线上 Java 诊断工具，适合查看方法调用、耗时、类加载、对象信息。

生产环境使用这些工具要遵守权限和变更规范。导出堆 dump 可能造成磁盘压力，`jmap -dump` 也可能让进程短暂停顿，必须评估影响。

## 场景一：Full GC 频繁

假设订单服务在大促期间频繁 Full GC，接口 P99 明显升高。第一步先确认 GC 情况：

```bash
jps -l
jstat -gcutil <pid> 1000 10
```

重点看 `YGC`、`YGCT`、`FGC`、`FGCT`、`O`。如果老年代使用率长期接近 100%，并且 Full GC 后下降不明显，说明很多对象仍然可达。

继续导出堆直方图：

```bash
jcmd <pid> GC.class_histogram | head -n 40
```

如果发现大量订单上下文对象：

```text
num     #instances         #bytes  class name
1       1250000            180000000  com.example.order.OrderContext
2       980000             120000000  com.example.promotion.PromotionResult
```

就要回到业务代码查缓存、静态集合、消息重试队列、批处理暂存区。供应链系统常见原因是把订单处理上下文放入本地缓存，但没有过期时间或清理机制。

```java
public class BadOrderContextCache {
    private static final Map<String, OrderContext> CACHE = new ConcurrentHashMap<>();

    public void put(OrderContext context) {
        CACHE.put(context.getOrderNo(), context);
    }
}
```

这类代码应该替换成有容量和过期策略的缓存，或者把上下文持久化到 Redis、数据库，并按业务状态清理。

## 场景二：OOM

OOM 发生时，先看异常类型：

```text
java.lang.OutOfMemoryError: Java heap space
java.lang.OutOfMemoryError: Metaspace
java.lang.OutOfMemoryError: Direct buffer memory
java.lang.OutOfMemoryError: unable to create native thread
```

建议生产默认开启：

```bash
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/data/dump
```

如果是 `Java heap space`，使用 MAT、VisualVM 或 JProfiler 分析 dump，重点看 Dominator Tree 和最大保留对象。如果是 `Metaspace`，检查动态类、代理、脚本、热部署。如果是 `Direct buffer memory`，检查 Netty、NIO、文件导入导出。如果是 `unable to create native thread`，检查线程池是否无界、容器 pids 限制和 `-Xss`。

供应链报表导出里的典型 OOM：

```java
public byte[] exportAllOutboundOrders() {
    List<OutboundOrder> orders = outboundRepository.findAll();
    Workbook workbook = excelWriter.write(orders);
    return workbook.toByteArray();
}
```

这个实现同时把全量订单和完整 Excel 放在内存里。更合理的方式是流式查询和流式写出：

```java
public void exportOutboundOrders(OutputStream outputStream) {
    try (StreamingExcelWriter writer = new StreamingExcelWriter(outputStream)) {
        long lastId = 0L;
        while (true) {
            List<OutboundOrder> page = outboundRepository.findPage(lastId, 1000);
            if (page.isEmpty()) {
                break;
            }
            writer.writeRows(page);
            lastId = page.get(page.size() - 1).getId();
        }
    }
}
```

## 场景三：CPU 飙高

CPU 高时，不能只重启。要先找到高 CPU 线程：

```bash
top -Hp <pid>
printf "%x\n" <tid>
jstack <pid> > /tmp/order-service.jstack
grep -n "<hexTid>" /tmp/order-service.jstack
```

如果线程栈显示大量时间消耗在价格计算、促销匹配、库存路由，可以继续结合业务日志和方法耗时定位。常见原因包括死循环、递归层级过深、正则表达式回溯、JSON 大对象序列化、锁竞争导致线程忙等。

例如库存路由中错误的递归：

```java
public WarehouseRoute findRoute(String skuCode, String warehouseCode) {
    WarehouseRoute route = routeRepository.find(skuCode, warehouseCode);
    if (route == null) {
        return findRoute(skuCode, fallbackWarehouse(warehouseCode));
    }
    return route;
}
```

如果 `fallbackWarehouse()` 在某些配置下返回原仓库编码，就会无限递归，最终 CPU 飙高或栈溢出。生产代码要增加访问集合和终止条件。

## 排查顺序建议

一次线上 JVM 故障可以按这个顺序处理：

1. 先止血：限流、摘流量、扩容、暂停批处理，保护核心交易链路。
2. 保留现场：保存 GC 日志、业务日志、线程 dump、必要时保存 heap dump。
3. 判断类型：CPU、内存、GC、线程、类加载、IO 还是外部依赖。
4. 缩小范围：结合发布时间、流量峰值、任务调度、业务操作。
5. 验证根因：用 dump、日志、监控和代码路径互相印证。
6. 修复并复盘：补监控、补限流、补压测、补容量评估。

JVM 排查能力的本质，是把现象变成证据，把证据映射到代码和业务。对供应链系统来说，订单高峰、仓储波次、库存同步、报表导出都可能触发 JVM 问题，排查时要同时看业务峰值和运行时状态。
