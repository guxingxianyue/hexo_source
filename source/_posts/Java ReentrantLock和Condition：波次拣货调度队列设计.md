---
title: Java ReentrantLock和Condition：波次拣货调度队列设计
date: 2025-05-08 09:30:00
tags: [Java, ReentrantLock, Condition, 并发队列, 仓储系统]
---

`ReentrantLock` 是 Java 显式锁。相比 `synchronized`，它提供了更丰富的控制能力：可以尝试加锁、可以响应中断、可以设置公平锁，还可以通过多个 `Condition` 管理不同等待条件。

在供应链仓储系统里，波次拣货是一个很适合解释 `ReentrantLock` 的场景。订单进入仓库后，系统会把多个订单合并成拣货波次。波次生成线程负责投放任务，拣货线程负责消费任务。如果没有合适的等待和唤醒机制，要么线程空转浪费 CPU，要么任务延迟处理。

## 波次队列协作流程

![ReentrantLock 和 Condition 波次队列流程](/images/tech-flowcharts/reentrantlock-condition-wave-flow.svg)

## 一个波次队列

需求如下：

- 波次生成器把 `PickWave` 放入队列。
- 拣货工作线程从队列获取波次。
- 队列满时，生成器等待。
- 队列空时，拣货线程等待。

这正是 `Condition` 的典型使用场景。

```java
public class PickWaveQueue {
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition notEmpty = lock.newCondition();
    private final Condition notFull = lock.newCondition();

    private final Deque<PickWave> queue = new ArrayDeque<>();
    private final int capacity;

    public PickWaveQueue(int capacity) {
        this.capacity = capacity;
    }

    public void put(PickWave wave) throws InterruptedException {
        lock.lockInterruptibly();
        try {
            while (queue.size() == capacity) {
                notFull.await();
            }
            queue.addLast(wave);
            notEmpty.signal();
        } finally {
            lock.unlock();
        }
    }

    public PickWave take() throws InterruptedException {
        lock.lockInterruptibly();
        try {
            while (queue.isEmpty()) {
                notEmpty.await();
            }
            PickWave wave = queue.removeFirst();
            notFull.signal();
            return wave;
        } finally {
            lock.unlock();
        }
    }
}
```

这个例子和 `BlockingQueue` 很像。真实项目中优先使用 JDK 的 `ArrayBlockingQueue` 或 `LinkedBlockingQueue`。这里手写是为了说明 `ReentrantLock` 和 `Condition` 的工作方式。

## 为什么用 while 而不是 if

等待条件必须用 `while`：

```java
while (queue.isEmpty()) {
    notEmpty.await();
}
```

原因有两个。第一，线程可能虚假唤醒。第二，线程被唤醒后不代表条件仍然成立。比如多个拣货线程都被唤醒，只有一个线程拿到了波次，其他线程再次检查时队列又空了。

供应链任务调度里，如果这里用 `if`，可能出现空队列取任务、重复消费或异常退出。

## tryLock 适合避免线程池耗尽

有些业务不适合无限等待锁。比如波次重算任务需要锁住某个仓库的计划上下文，如果拿不到锁，可以返回“系统正在计算，请稍后重试”。

```java
public boolean rebuildWavePlan(long warehouseId) throws InterruptedException {
    if (!lock.tryLock(3, TimeUnit.SECONDS)) {
        return false;
    }
    try {
        loadOrders(warehouseId);
        allocateBins(warehouseId);
        savePlan(warehouseId);
        return true;
    } finally {
        lock.unlock();
    }
}
```

`tryLock` 的价值是给系统退路。线程池里的线程不应该因为等待一把锁全部卡死。

## 公平锁和非公平锁

`ReentrantLock` 默认是非公平锁。新来的线程可能插队获取锁，吞吐通常更高。

```java
private final ReentrantLock lock = new ReentrantLock();
```

公平锁按等待顺序获取锁：

```java
private final ReentrantLock fairLock = new ReentrantLock(true);
```

供应链后台任务多数更关注吞吐，非公平锁更常用。只有在明确存在饥饿问题，比如某类低优先级补货任务长期拿不到锁，才需要评估公平锁。但公平锁会增加调度成本，不应该默认使用。

## 和数据库事务配合

Java 锁保护的是内存队列，不保护数据库里的波次状态。真正创建波次时仍然要用数据库状态条件防重：

```sql
UPDATE scm_pick_wave
SET status = 'PROCESSING'
WHERE id = #{waveId}
  AND status = 'WAIT_PROCESS';
```

Java 工作线程拿到波次后：

```java
@Transactional
public void process(PickWave wave) {
    int affected = waveMapper.markProcessing(wave.id());
    if (affected != 1) {
        return;
    }
    allocatePickTasks(wave);
    waveMapper.markReady(wave.id());
}
```

即使同一个波次因为重试被投递两次，数据库状态条件也能保证只有一个线程真正处理成功。

## 小结

`ReentrantLock` 适合需要超时、可中断、多个等待条件的并发控制。供应链系统里的波次队列、任务调度、仓库计划重算都能用它解释。但真实项目中，能用成熟并发容器就先用并发容器；数据库状态变更必须继续依赖条件更新，不能只靠 JVM 锁。
