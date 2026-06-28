---
title: Java并发集合与排查：仓储任务并发安全怎么落地
date: 2022-05-30 10:20:00
tags: [Java, ConcurrentHashMap, BlockingQueue, CAS, 死锁, 仓储系统]
---

Java 多线程最终要落到数据结构和排查能力上。供应链系统里，仓储任务调度、库存缓存、波次队列、接口指标都会用到并发集合和原子类。选择正确的数据结构，可以减少手写锁；具备排查能力，才能在线上出现卡顿时定位问题。

## 数据结构和排查流程

![并发集合和线程排查流程](/images/tech-flowcharts/concurrent-collections-troubleshooting-flow.svg)

## ConcurrentHashMap：本地任务状态缓存

仓储系统可能需要缓存正在处理的上架任务，避免同一个任务在当前实例内重复提交：

```java
public class PutawayTaskRegistry {
    private final ConcurrentHashMap<Long, PutawayTask> runningTasks = new ConcurrentHashMap<>();

    public boolean register(PutawayTask task) {
        return runningTasks.putIfAbsent(task.id(), task) == null;
    }

    public void unregister(Long taskId) {
        runningTasks.remove(taskId);
    }
}
```

`putIfAbsent` 是原子操作。多个线程同时注册同一个任务，只有一个会成功。

注意，这只保护当前 JVM。多实例部署时，仍然要靠数据库状态条件防重：

```sql
UPDATE scm_putaway_task
SET status = 'RUNNING'
WHERE id = #{taskId}
  AND status = 'WAITING';
```

## BlockingQueue：生产者消费者

仓库波次任务可以用阻塞队列实现生产者消费者：

```java
public class WaveDispatchQueue {
    private final BlockingQueue<WaveTask> queue = new ArrayBlockingQueue<>(1000);

    public void submit(WaveTask task) throws InterruptedException {
        queue.put(task);
    }

    public WaveTask take() throws InterruptedException {
        return queue.take();
    }
}
```

生产者生成波次任务，消费者线程处理任务：

```java
public void startWorkers() {
    for (int i = 0; i < 8; i++) {
        executor.execute(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    WaveTask task = queue.take();
                    waveService.dispatch(task);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        });
    }
}
```

阻塞队列的好处是自然支持等待和唤醒，不需要自己写 `wait/notify`。

## CopyOnWriteArrayList：读多写少配置

仓库作业规则通常读多写少，比如上架策略规则：

```java
public class PutawayRuleHolder {
    private final CopyOnWriteArrayList<PutawayRule> rules = new CopyOnWriteArrayList<>();

    public List<PutawayRule> currentRules() {
        return rules;
    }

    public void reload(List<PutawayRule> latest) {
        rules.clear();
        rules.addAll(latest);
    }
}
```

`CopyOnWriteArrayList` 写入时复制数组，读取时不加锁。它适合规则、配置、监听器列表，不适合高频写入的数据。

## CAS 和 AtomicReference

本地策略快照可以用 `AtomicReference` 原子替换：

```java
public class RoutingPolicyCache {
    private final AtomicReference<RoutingPolicy> policyRef =
        new AtomicReference<>(RoutingPolicy.defaultPolicy());

    public RoutingPolicy current() {
        return policyRef.get();
    }

    public void refresh(RoutingPolicy latest) {
        policyRef.set(latest);
    }
}
```

如果要防止旧版本覆盖新版本：

```java
public boolean refreshIfNewer(RoutingPolicy latest) {
    while (true) {
        RoutingPolicy current = policyRef.get();
        if (latest.version() <= current.version()) {
            return false;
        }
        if (policyRef.compareAndSet(current, latest)) {
            return true;
        }
    }
}
```

这适合单 JVM 内的配置引用。业务库存余额不应该用本地 CAS 保存，因为库存需要跨实例一致、事务回滚和审计。

## 死锁排查

Java 死锁常见于多个线程以不同顺序获取锁。例如两个仓储任务同时锁两个库位：

```java
synchronized (binA) {
    synchronized (binB) {
        transfer();
    }
}
```

另一个线程反过来：

```java
synchronized (binB) {
    synchronized (binA) {
        transfer();
    }
}
```

解决办法是固定加锁顺序：

```java
public void transfer(Bin from, Bin to) {
    Bin first = from.id() < to.id() ? from : to;
    Bin second = from.id() < to.id() ? to : from;

    synchronized (first) {
        synchronized (second) {
            doTransfer(from, to);
        }
    }
}
```

线上排查可以用：

```bash
jstack <pid>
```

或者 Arthas：

```bash
thread -b
```

重点看线程是否大量 `BLOCKED`，以及堆栈里等待的是哪把锁。

## 线上排查顺序

仓储任务卡顿时，可以按这个顺序排查：

1. 看线程池：活跃线程数、队列长度、拒绝次数是否异常。
2. 看线程状态：`jstack` 或 Arthas `thread` 查看是否大量 `BLOCKED`、`WAITING`。
3. 看锁对象：定位堆栈里等待的是 Java 对象锁、数据库锁，还是队列阻塞。
4. 看业务状态：仓储任务是否卡在同一个波次、库位、SKU 或外部 WMS 调用。
5. 看数据一致性：确认任务状态机是否允许重复执行、失败重试和人工恢复。

排查时不要只看到 `ConcurrentHashMap` 就认为线程安全已经解决。并发集合只能保证集合自身操作安全，不能自动保证“任务状态 + 数据库记录 + 外部调用”的业务一致性。

## 小结

并发集合和原子类能减少手写锁，让并发代码更清晰。供应链系统里，`ConcurrentHashMap` 适合本地任务注册，`BlockingQueue` 适合生产者消费者，`CopyOnWriteArrayList` 适合读多写少规则，`AtomicReference` 适合配置快照替换。核心业务数据仍然要用数据库状态机和事务保护。线上卡顿时，要能用 `jstack`、Arthas 定位线程阻塞和死锁。
