---
title: Java volatile与JMM：库存同步任务的可见性问题
date: 2025-04-29 10:10:00
tags: [Java, volatile, JMM, 可见性, 库存系统]
---

`volatile` 是 Java 并发里经常被误用的关键字。它能保证变量修改对其他线程可见，并禁止相关指令重排，但它不是互斥锁，也不能保证复合操作的原子性。

供应链系统中，`volatile` 最适合的场景是任务开关、配置引用、状态标记。比如库存同步任务需要能被后台管理页面停止，或者定时任务需要感知配置已刷新。

## JMM 要解决什么

Java 内存模型规定了线程如何从主内存读取变量、如何把修改写回主内存，以及什么情况下一个线程的写入对另一个线程可见。

如果没有同步手段，一个线程修改变量，另一个线程不一定马上看到。CPU 缓存、编译器优化、指令重排都会让多线程程序表现得不符合直觉。

库存同步任务的停止标志是典型例子：

```java
public class InventorySyncTask implements Runnable {
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

管理线程调用 `stop()` 后，工作线程可能仍然看不到 `running = false`，导致任务停不下来。

## 使用 volatile 修复可见性

```java
public class InventorySyncTask implements Runnable {
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

`volatile` 写入会把修改刷新出去，`volatile` 读取会从可见位置重新读取。这样管理线程修改停止标志后，工作线程能及时观察到。

这类代码在供应链系统中很常见：库存同步、价格同步、承运商轨迹拉取、供应商主数据刷新，都可能需要停止标志。

## volatile 不保证 count++ 安全

错误示例：

```java
public class SyncMetrics {
    private volatile int successCount = 0;

    public void incrementSuccess() {
        successCount++;
    }
}
```

`successCount++` 不是一个原子操作，它包含读取、加一、写回。多个线程同时执行时会丢失更新。

正确写法可以用 `AtomicInteger`：

```java
public class SyncMetrics {
    private final AtomicInteger successCount = new AtomicInteger();

    public void incrementSuccess() {
        successCount.incrementAndGet();
    }
}
```

如果是高并发统计，比如每秒记录库存同步成功数，用 `LongAdder` 更合适：

```java
public class SyncMetrics {
    private final LongAdder successCount = new LongAdder();

    public void incrementSuccess() {
        successCount.increment();
    }

    public long successCount() {
        return successCount.sum();
    }
}
```

## 配置引用的安全发布

`volatile` 还适合发布不可变配置对象。比如供应链系统里有库存分配策略：

```java
public class AllocationPolicyHolder {
    private volatile AllocationPolicy policy = AllocationPolicy.defaultPolicy();

    public AllocationPolicy current() {
        return policy;
    }

    public void refresh(AllocationPolicy newPolicy) {
        this.policy = newPolicy;
    }
}
```

只要 `AllocationPolicy` 本身是不可变对象，刷新时整体替换引用，读线程就能看到完整的新配置。

不要这样做：

```java
policy.getRules().add(newRule);
```

如果对象内部可变，即使引用是 `volatile`，内部集合的并发修改仍然不安全。配置对象应设计成不可变：

```java
public final class AllocationPolicy {
    private final List<Rule> rules;

    public AllocationPolicy(List<Rule> rules) {
        this.rules = List.copyOf(rules);
    }

    public List<Rule> rules() {
        return rules;
    }
}
```

## happens-before 关系

`volatile` 写 happens-before 后续对同一变量的读。简单理解：线程 A 在写 volatile 变量之前做的普通写入，线程 B 读到这个 volatile 变量后，也能看到这些普通写入。

例如：

```java
private Map<String, Integer> latestStock;
private volatile boolean ready;

public void load() {
    latestStock = loadFromDatabase();
    ready = true;
}

public int query(String sku) {
    if (!ready) {
        return 0;
    }
    return latestStock.getOrDefault(sku, 0);
}
```

当查询线程读到 `ready = true` 后，可以看到 `latestStock` 的赋值。但这个写法仍要求 `latestStock` 后续不被并发修改。更稳的做法是用不可变 Map 或整体替换引用。

## 小结

`volatile` 适合表达“状态变化要被其他线程看到”。它不适合保护多个变量的一致性，也不适合做计数器自增。供应链系统里，任务停止标志、配置引用、只写一次的发布状态可以使用 `volatile`；库存扣减、单据状态变更、计数统计要用锁、原子类或数据库条件更新。

