---
title: Java线程池实战：订单履约任务如何稳定提吞吐
date: 2022-05-16 10:00:00
tags: [Java, 线程池, ThreadPoolExecutor, 订单履约, 供应链系统]
---

线程池是 Java 多线程在业务系统中最常用的落地方式。它解决两个问题：复用线程，减少创建销毁成本；限制并发，避免请求无限堆积压垮系统。供应链系统里的订单履约、库存同步、物流轨迹拉取、报表生成，都应该用线程池管理并发。

## 履约线程池流程

![订单履约线程池流程](/images/tech-flowcharts/thread-pool-fulfillment-flow.svg)

## 不要无限创建线程

错误示例：

```java
for (Long orderId : orderIds) {
    new Thread(() -> fulfillmentService.fulfill(orderId)).start();
}
```

如果一次批处理有 5000 个订单，这段代码会创建 5000 个线程。线程本身占内存，调度也有成本，下游数据库、WMS、TMS 都可能被打爆。

应该使用 `ThreadPoolExecutor`：

```java
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    8,
    16,
    60,
    TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(1000),
    new ThreadFactory() {
        private final AtomicInteger index = new AtomicInteger();

        @Override
        public Thread newThread(Runnable r) {
            return new Thread(r, "fulfillment-worker-" + index.incrementAndGet());
        }
    },
    new ThreadPoolExecutor.CallerRunsPolicy()
);
```

这个线程池最多 16 个工作线程，队列最多缓存 1000 个任务。超过能力后，`CallerRunsPolicy` 会让提交任务的线程自己执行，形成反压。

## 七个核心参数

`ThreadPoolExecutor` 的关键参数包括：

- `corePoolSize`：核心线程数。
- `maximumPoolSize`：最大线程数。
- `keepAliveTime`：非核心线程空闲多久回收。
- `unit`：时间单位。
- `workQueue`：任务队列。
- `threadFactory`：线程工厂。
- `handler`：拒绝策略。

供应链系统里，线程数不是越大越好。订单履约通常包含数据库、库存服务、仓储服务、物流服务调用，属于 IO 密集型，可以适度提高线程数。但如果下游 TMS 每秒只允许 100 次请求，线程池再大也只会制造超时。

## 订单履约 demo

批量履约订单时，可以这样提交任务：

```java
public void fulfillBatch(List<Long> orderIds) {
    for (Long orderId : orderIds) {
        executor.execute(() -> {
            try {
                fulfillmentService.fulfill(orderId);
            } catch (Exception e) {
                fulfillmentLogService.recordFailed(orderId, e.getMessage());
            }
        });
    }
}
```

任务内部要保证幂等：

```java
@Transactional
public void fulfill(Long orderId) {
    int affected = orderMapper.markFulfilling(orderId);
    if (affected != 1) {
        return;
    }

    inventoryService.reserve(orderId);
    warehouseTaskService.createPickTask(orderId);
    orderMapper.markFulfilled(orderId);
}
```

对应状态更新：

```sql
UPDATE scm_sales_order
SET status = 'FULFILLING'
WHERE id = #{orderId}
  AND status = 'WAIT_FULFILL';
```

线程池负责并发执行，数据库状态机负责避免重复履约。

## 队列选择

常见队列：

- `ArrayBlockingQueue`：有界数组队列，容量固定，适合明确限流。
- `LinkedBlockingQueue`：链表队列，可有界也可无界；业务中必须设置容量。
- `SynchronousQueue`：不存储任务，直接移交线程，适合快速扩容线程的场景。
- `PriorityBlockingQueue`：优先级队列，适合高优先级订单先处理。

供应链系统建议优先使用有界队列。无界队列在高峰期会隐藏问题，直到内存被耗尽。

## 监控线程池

线程池必须监控：

```java
public ThreadPoolStats stats() {
    return new ThreadPoolStats(
        executor.getPoolSize(),
        executor.getActiveCount(),
        executor.getQueue().size(),
        executor.getCompletedTaskCount()
    );
}
```

核心指标：

- 活跃线程数是否长期接近最大线程数。
- 队列长度是否持续增长。
- 拒绝任务是否出现。
- 单任务耗时是否变长。

如果队列持续增长，不要只加线程。要确认瓶颈是数据库、外部接口、锁等待还是代码慢。

## 容量估算

线程池参数要从业务容量倒推，而不是凭经验随手写。以订单履约为例：

1. 单个履约任务平均耗时 200ms。
2. 其中 150ms 在等待数据库、库存服务、WMS 或 TMS。
3. 目标吞吐是每秒 80 单。

粗略估算并发数：

```text
并发数 = 目标吞吐 * 平均耗时
      = 80 * 0.2
      = 16
```

所以核心线程数可以从 16 附近开始压测，再结合 CPU、数据库连接池、WMS 限流和错误率调整。队列大小也要有业务含义，例如最多允许堆积 1000 单，超过后让调用方降级、延迟重试或进入消息队列，而不是无限排队。

线程池调优的目标是稳定吞吐，不是把线程数调到最大。高峰期如果队列持续上涨，说明系统消费能力不足，需要扩容、拆批、限流或优化单任务耗时。

## 小结

线程池的作用是稳定地控制并发，而不是无上限地提高并发。供应链系统中，线程池适合订单履约、库存同步、物流轨迹拉取等后台任务。设计时要使用有界队列、明确拒绝策略、处理任务异常、保证业务幂等，并持续监控线程池运行状态。
