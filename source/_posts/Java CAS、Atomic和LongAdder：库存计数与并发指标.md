---
title: Java CAS、Atomic和LongAdder：库存计数与并发指标
date: 2025-06-05 09:30:00
tags: [Java, CAS, Atomic, LongAdder, 并发编程]
---

CAS 是 Compare And Swap，比较并交换。它是很多无锁并发工具的基础。Java 里的 `AtomicInteger`、`AtomicLong`、`AtomicReference`、`LongAdder` 都和 CAS 思路有关。

供应链系统里，CAS 适合应用层内存计数、指标统计、状态引用切换。它不适合替代数据库里的库存扣减。库存是跨节点共享的业务数据，最终必须由数据库条件更新、唯一约束或专门库存服务保证一致。

## CAS 和指标统计流程

![CAS 原子类和指标统计流程](/images/tech-flowcharts/cas-atomic-metrics-flow.svg)

## AtomicInteger 的基本用法

库存同步任务需要统计本轮处理成功数：

```java
public class InventorySyncMetrics {
    private final AtomicInteger success = new AtomicInteger();
    private final AtomicInteger failed = new AtomicInteger();

    public void markSuccess() {
        success.incrementAndGet();
    }

    public void markFailed() {
        failed.incrementAndGet();
    }

    public int successCount() {
        return success.get();
    }
}
```

`incrementAndGet()` 内部会反复尝试 CAS：读取旧值，计算新值，尝试把旧值替换成新值。如果期间其他线程已经修改，就重试。

这比 `volatile int count++` 安全，因为复合操作由原子类保证。

## AtomicReference 切换配置

供应链系统常有策略配置，比如库存分配策略。可以用 `AtomicReference` 原子替换整份不可变配置：

```java
public class AllocationConfigCenter {
    private final AtomicReference<AllocationConfig> configRef =
        new AtomicReference<>(AllocationConfig.defaultConfig());

    public AllocationConfig current() {
        return configRef.get();
    }

    public void refresh(AllocationConfig latest) {
        configRef.set(latest);
    }
}
```

如果需要基于旧配置做条件更新：

```java
public boolean refreshIfVersionMatch(AllocationConfig latest) {
    AllocationConfig current = configRef.get();
    if (latest.version() <= current.version()) {
        return false;
    }
    return configRef.compareAndSet(current, latest);
}
```

这适合本地配置引用。不要把它理解为分布式配置一致性的完整方案。

## ABA 问题

CAS 的经典问题是 ABA：线程看到值从 A 变成 B，又变回 A，以为没有变化，但实际中间发生过修改。

比如内存里的任务状态：

```text
WAIT -> RUNNING -> WAIT
```

另一个线程只看最终还是 `WAIT`，可能误以为任务从未被处理。

可以用版本号解决：

```java
AtomicStampedReference<String> status =
    new AtomicStampedReference<>("WAIT", 0);

int[] stampHolder = new int[1];
String current = status.get(stampHolder);

boolean success = status.compareAndSet(
    current,
    "RUNNING",
    stampHolder[0],
    stampHolder[0] + 1
);
```

业务系统里更常见的是数据库版本号：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - 5,
    version = version + 1
WHERE id = #{id}
  AND version = #{oldVersion}
  AND available_qty >= 5;
```

这就是乐观锁。它比 Java 内存 CAS 更适合跨实例共享数据。

## LongAdder 适合高并发统计

高并发下，所有线程竞争同一个 `AtomicLong` 可能形成热点。`LongAdder` 通过分散计数降低竞争，最终求和。

```java
public class ApiMetrics {
    private final LongAdder reserveStockCount = new LongAdder();

    public void markReserveStock() {
        reserveStockCount.increment();
    }

    public long reserveStockCount() {
        return reserveStockCount.sum();
    }
}
```

它适合接口调用次数、同步成功数、报表处理行数这些指标。它不适合要求每次读取都严格精确的业务余额。

库存可售数不能这样做：

```java
private final LongAdder salableStock = new LongAdder();
```

因为库存是强业务数据，不是指标。它要支持事务、回滚、审计和跨节点一致性。

## CAS 与数据库条件更新的类比

CAS 的思想和数据库乐观锁很像：都要求“当前值还是我预期的值”才更新。

Java CAS：

```java
compareAndSet(oldValue, newValue)
```

数据库乐观锁：

```sql
UPDATE scm_purchase_order
SET status = 'APPROVED',
    version = version + 1
WHERE id = #{id}
  AND status = 'WAIT_APPROVE'
  AND version = #{version};
```

区别在于 Java CAS 只作用于当前 JVM 内存，数据库乐观锁作用于持久化数据，能被多个应用实例共同遵守。

## 使用边界

CAS 和原子类适合三类数据：

1. 指标：接口调用次数、同步成功数、失败数。
2. 引用：不可变配置、策略快照、路由规则版本。
3. 本地状态：单 JVM 内的轻量状态切换。

不适合三类数据：

1. 需要事务回滚的数据，例如库存扣减。
2. 需要跨实例一致的数据，例如订单审核状态。
3. 需要审计流水的数据，例如财务结算和库存流水。

如果一个数据需要“查得出历史、失败能回滚、多个实例共同遵守”，就应该进入数据库事务和业务状态机，而不是停留在 JVM 原子变量里。

## 小结

CAS 和原子类适合低成本地保护内存状态，尤其是计数、配置引用、轻量状态切换。供应链系统可以用它们做同步指标、缓存版本、任务状态引用。但库存扣减、单据审核、结算过账这些核心数据必须使用数据库条件更新或事务锁。不要把 JVM 内的原子性误认为全系统一致性。
