---
title: Java内存模型与锁：库存同步中的可见性和互斥
date: 2022-05-10 09:40:00
tags: [Java, JMM, synchronized, volatile, 供应链系统]
---

Java 多线程的核心问题可以归纳为三类：原子性、可见性、有序性。Java 内存模型，也就是 JMM，定义了线程之间如何看见彼此的写入，以及哪些同步动作能建立 happens-before 关系。供应链系统里，库存同步、价格缓存、仓库配置刷新都离不开这些基础。

## 可见性和互斥流程

![JMM 可见性和锁边界流程](/images/tech-flowcharts/jmm-visibility-lock-flow.svg)

## 可见性问题

库存同步任务通常有一个停止标志：

```java
public class InventorySyncJob implements Runnable {
    private boolean running = true;

    public void stop() {
        running = false;
    }

    @Override
    public void run() {
        while (running) {
            syncOnce();
        }
    }
}
```

管理线程调用 `stop()` 后，工作线程不一定马上看到 `running = false`。这就是可见性问题。

可以使用 `volatile`：

```java
public class InventorySyncJob implements Runnable {
    private volatile boolean running = true;

    public void stop() {
        running = false;
    }

    @Override
    public void run() {
        while (running) {
            syncOnce();
        }
    }
}
```

`volatile` 保证写入对其他线程可见，并限制相关指令重排。它适合任务开关、配置引用、状态标志。

## volatile 不保证复合操作原子性

下面这个计数器是错误的：

```java
public class SyncCounter {
    private volatile int successCount;

    public void success() {
        successCount++;
    }
}
```

`successCount++` 包含读取、加一、写回三个步骤。多个线程同时执行会丢失更新。正确方式是使用原子类：

```java
public class SyncCounter {
    private final AtomicInteger successCount = new AtomicInteger();

    public void success() {
        successCount.incrementAndGet();
    }
}
```

如果是高并发指标统计，可以用 `LongAdder`：

```java
public class SyncCounter {
    private final LongAdder successCount = new LongAdder();

    public void success() {
        successCount.increment();
    }

    public long value() {
        return successCount.sum();
    }
}
```

## synchronized 解决互斥

如果多个线程要修改同一个本地库存快照 Map，需要互斥控制：

```java
public class InventorySnapshotCache {
    private final Map<String, Integer> cache = new HashMap<>();

    public synchronized void put(String key, Integer qty) {
        cache.put(key, qty);
    }

    public synchronized Integer get(String key) {
        return cache.get(key);
    }
}
```

`synchronized` 修饰实例方法时，锁对象是 `this`。同一个对象上的同步方法互斥。

更推荐使用私有锁对象，避免外部代码锁住当前实例：

```java
public class InventorySnapshotCache {
    private final Object lock = new Object();
    private final Map<String, Integer> cache = new HashMap<>();

    public void put(String key, Integer qty) {
        synchronized (lock) {
            cache.put(key, qty);
        }
    }

    public Integer get(String key) {
        synchronized (lock) {
            return cache.get(key);
        }
    }
}
```

## 锁的边界

供应链系统一般是多实例部署。`synchronized` 只能保护当前 JVM 内存，不能保护数据库里的库存余额。如果两个应用实例同时扣同一条库存，Java 本地锁没有任何作用。

库存扣减必须落到数据库条件更新：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - #{qty},
    locked_qty = locked_qty + #{qty}
WHERE warehouse_id = #{warehouseId}
  AND sku_id = #{skuId}
  AND available_qty >= #{qty};
```

Java 锁适合保护本地缓存、内存队列、对象状态；数据库事务和行锁负责保护最终业务数据。

## happens-before 怎么理解

JMM 里最实用的判断工具是 happens-before。它不是描述时间先后，而是描述一个线程的写入是否对另一个线程可见。

常见规则包括：

1. 对一个 `volatile` 变量的写，happens-before 后续对这个变量的读。
2. 对一个锁的解锁，happens-before 后续对同一把锁的加锁。
3. 线程 `start()` 之前的操作，happens-before 新线程中的操作。
4. 一个线程中的操作，按程序顺序 happens-before 后续操作。

例如库存规则缓存刷新时，可以使用整体替换引用：

```java
public class InventoryRuleHolder {
    private volatile InventoryRuleSnapshot snapshot = InventoryRuleSnapshot.empty();

    public void refresh() {
        snapshot = inventoryRuleRepository.loadSnapshot();
    }

    public InventoryRuleSnapshot current() {
        return snapshot;
    }
}
```

这里 `volatile` 保证查询线程能看到新的快照引用。但快照对象本身应该是不可变的，否则引用可见不代表内部集合并发修改安全。

## 小结

JMM 是理解 Java 多线程的基础。`volatile` 解决可见性和有序性，不解决复合操作原子性；`synchronized` 解决单 JVM 内共享状态的互斥；数据库锁解决跨实例的业务数据一致性。供应链系统里要明确每把锁保护的对象，不能用本地锁替代数据库并发控制。
