---
title: Java锁总览：从synchronized到AQS保护供应链单据
date: 2025-03-20 10:15:00
tags: [Java, 并发编程, 锁, AQS, 供应链系统]
---

Java 锁解决的是 JVM 内多个线程同时访问共享对象的问题。供应链系统虽然最终数据在数据库里，但 Java 应用层也有大量共享状态：本地缓存、任务队列、单据处理器、库存同步批次、报表聚合结果。如果这些状态没有并发控制，数据库锁也救不了应用层的混乱。

Java 锁的学习路线可以从四层理解：`synchronized`、`volatile`、`java.util.concurrent.locks`、AQS/CAS。业务上要回答的不是“哪个锁更高级”，而是“这个共享数据是否必须互斥，是否需要等待条件，是否读多写少，是否可以用无锁原子变量”。

## Java 锁选择流程

![Java 锁选择流程](/images/tech-flowcharts/java-lock-overview-flow.svg)

## 一个供应链单据处理例子

假设系统里有一个本地任务分发器，把待审核采购单放到内存队列里，由多个工作线程消费：

```java
public class PurchaseApproveWorker {
    private final Queue<Long> queue = new ArrayDeque<>();

    public void submit(Long purchaseOrderId) {
        queue.add(purchaseOrderId);
    }

    public Long poll() {
        return queue.poll();
    }
}
```

这段代码在单线程下没问题，在多线程下有问题。`ArrayDeque` 不是线程安全的，多个线程同时 `add` 和 `poll` 可能导致数据结构状态损坏、任务丢失或重复消费。

最直接的修复方式是用 `synchronized`：

```java
public class PurchaseApproveWorker {
    private final Queue<Long> queue = new ArrayDeque<>();

    public synchronized void submit(Long purchaseOrderId) {
        queue.add(purchaseOrderId);
    }

    public synchronized Long poll() {
        return queue.poll();
    }
}
```

这保证了同一时间只有一个线程能访问 `queue`。但它还不完整：消费者如果发现队列为空，只能不断轮询。更好的方式是使用 `BlockingQueue`，让成熟并发容器处理等待和唤醒：

```java
public class PurchaseApproveWorker {
    private final BlockingQueue<Long> queue = new LinkedBlockingQueue<>();

    public void submit(Long purchaseOrderId) {
        queue.offer(purchaseOrderId);
    }

    public Long take() throws InterruptedException {
        return queue.take();
    }
}
```

工程上优先使用 JDK 已经验证过的并发容器，而不是手写锁。手写锁只有在业务控制非常明确时才值得做。

## synchronized 解决互斥

`synchronized` 是 Java 最基础的互斥锁。它可以修饰实例方法、静态方法和代码块。

```java
public class InventoryLocalCache {
    private final Map<String, Integer> stock = new HashMap<>();

    public synchronized void put(String skuKey, int qty) {
        stock.put(skuKey, qty);
    }

    public synchronized int get(String skuKey) {
        return stock.getOrDefault(skuKey, 0);
    }
}
```

实例方法上的锁对象是当前实例 `this`。静态方法上的锁对象是 Class 对象。代码块可以显式指定锁对象：

```java
private final Object lock = new Object();

public void refresh(String skuKey, int qty) {
    synchronized (lock) {
        stock.put(skuKey, qty);
    }
}
```

供应链系统里如果多个方法保护的是同一份共享状态，必须使用同一把锁。否则看似加锁，实际互斥范围不一致。

## volatile 解决可见性

`volatile` 不是互斥锁，它解决的是可见性和指令重排问题。

库存同步任务常见一个停止标志：

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

如果没有 `volatile`，一个线程调用 `stop()` 后，工作线程可能长时间看不到 `running = false`。加上 `volatile` 后，写入对其他线程可见。

但 `volatile` 不能保证复合操作原子性：

```java
volatile int count = 0;
count++;
```

`count++` 包含读、加、写三个步骤，多线程下仍然会丢失更新。供应链系统里统计已处理单据数，不应该用 `volatile int++`，可以使用 `AtomicInteger` 或 `LongAdder`。

## ReentrantLock 解决更复杂的锁控制

`ReentrantLock` 提供了比 `synchronized` 更明确的能力：可中断锁、超时尝试、公平锁、多个条件队列。

```java
public class ShipmentAllocator {
    private final ReentrantLock lock = new ReentrantLock();

    public boolean allocate(Long shipmentId) throws InterruptedException {
        if (!lock.tryLock(2, TimeUnit.SECONDS)) {
            return false;
        }
        try {
            return doAllocate(shipmentId);
        } finally {
            lock.unlock();
        }
    }
}
```

在波次分配、批量调度、任务抢占这类场景里，`tryLock` 比无期限等待更实用。拿不到锁就返回失败或稍后重试，避免线程池被全部阻塞。

## AQS 是很多并发工具的基础

AQS 是 `AbstractQueuedSynchronizer`，它不是业务代码每天直接使用的 API，但理解它有助于理解 `ReentrantLock`、`Semaphore`、`CountDownLatch` 等工具。

AQS 的核心是一个 `state` 状态值和一个等待队列。线程获取锁失败后进入队列，等待前驱节点释放后被唤醒。

供应链批处理里常见 `CountDownLatch`：

```java
CountDownLatch latch = new CountDownLatch(3);

executor.submit(() -> {
    loadInventory();
    latch.countDown();
});
executor.submit(() -> {
    loadPurchaseOrders();
    latch.countDown();
});
executor.submit(() -> {
    loadSupplierConfig();
    latch.countDown();
});

latch.await();
generatePlanningResult();
```

它不是锁业务对象，而是协调多个线程阶段。理解 AQS 后，可以清楚地区分互斥锁和线程协作工具。

## 选择建议

能用无共享状态，就不要加锁。比如每个请求创建自己的上下文对象。

能用数据库条件更新，就不要在应用层用本地锁保护跨节点数据。多实例部署时，本地 Java 锁只在单个 JVM 内有效，不能保护整个集群。

能用并发容器，就不要手写锁。比如 `ConcurrentHashMap`、`BlockingQueue`、`LongAdder`。

确实需要保护对象内部状态时，简单互斥用 `synchronized`。需要超时、可中断、多个条件队列时，用 `ReentrantLock`。读多写少时考虑读写锁。计数器和状态 CAS 更新考虑原子类。

## 小结

Java 锁和 MySQL 锁保护的范围不同。Java 锁保护 JVM 内存对象，MySQL 锁保护数据库记录。供应链系统里的正确做法通常是两者配合：应用层锁保护本地状态，数据库锁保护最终数据一致性。不要用 Java 本地锁代替数据库并发控制，也不要把所有并发问题都推给数据库。
