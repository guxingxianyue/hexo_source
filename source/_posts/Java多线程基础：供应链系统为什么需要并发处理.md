---
title: Java多线程基础：供应链系统为什么需要并发处理
date: 2022-05-05 09:30:00
tags: [Java, 多线程, 并发编程, 供应链系统]
---

Java 多线程不是为了把代码写复杂，而是为了在合适的业务场景里提高吞吐、降低等待时间、充分利用 CPU 和 IO 资源。供应链系统里有大量典型场景：订单创建后要校验库存、校验客户信用、计算运费、匹配促销、写操作日志；仓库出库时要生成波次、分配库位、通知 WMS、刷新库存快照。这些动作有些可以并行，有些必须串行，多线程的价值就是把这两类工作区分清楚。

## 并发决策流程

![Java 多线程决策流程](/images/tech-flowcharts/java-concurrency-decision-flow.svg)

## 线程和进程

进程是操作系统资源分配的基本单位，线程是 CPU 调度执行的基本单位。一个 Java 应用进程里可以有很多线程，比如 Tomcat 请求线程、业务线程池线程、GC 线程、定时任务线程。

在供应链系统中，一个订单接口请求通常由一个 Web 容器线程处理。如果接口里所有操作都串行执行，请求耗时会被每一步累加。如果某些步骤没有依赖关系，就可以并行执行。

## 线程生命周期

Java 线程常见状态包括：

- `NEW`：线程对象已创建但未启动。
- `RUNNABLE`：可运行，等待 CPU 调度或正在执行。
- `BLOCKED`：等待进入 synchronized 临界区。
- `WAITING`：无限期等待其他线程通知。
- `TIMED_WAITING`：限时等待，比如 `sleep`、带超时的 `wait`。
- `TERMINATED`：线程执行结束。

排查供应链批处理卡顿时，线程状态很关键。大量 `BLOCKED` 说明锁竞争严重，大量 `WAITING` 可能是队列无任务或等待条件未满足，大量 `RUNNABLE` 但 CPU 很高可能是计算任务过重或死循环。

## 创建线程的方式

最原始的方式是直接创建 `Thread`：

```java
Thread thread = new Thread(() -> {
    System.out.println("同步库存快照");
});
thread.start();
```

这种方式适合理解原理，不适合业务系统大量使用。真实项目应该使用线程池，避免频繁创建和销毁线程。

`Runnable` 没有返回值，适合只执行动作：

```java
Runnable task = () -> inventorySyncService.syncWarehouse(8L);
new Thread(task).start();
```

`Callable` 有返回值，可以配合 `Future`：

```java
Callable<Integer> task = () -> inventoryQueryService.countAvailableSku(8L);
FutureTask<Integer> future = new FutureTask<>(task);
new Thread(future).start();
Integer count = future.get();
```

但业务里更常用线程池提交任务。

## 供应链订单校验的并行 demo

创建销售订单时，下面三个校验互不依赖：

- 查询库存是否足够。
- 查询客户信用额度。
- 查询承运商是否覆盖收货地址。

串行写法：

```java
public OrderCheckResult checkOrder(OrderCreateCommand command) {
    InventoryCheckResult inventory = inventoryService.check(command.items());
    CreditCheckResult credit = creditService.check(command.customerId(), command.amount());
    CarrierCheckResult carrier = carrierService.check(command.address());
    return OrderCheckResult.merge(inventory, credit, carrier);
}
```

如果三个调用分别耗时 80ms、60ms、50ms，总耗时至少接近 190ms。可以用线程池并行：

```java
public OrderCheckResult checkOrder(OrderCreateCommand command) throws Exception {
    Future<InventoryCheckResult> inventoryFuture =
        executor.submit(() -> inventoryService.check(command.items()));

    Future<CreditCheckResult> creditFuture =
        executor.submit(() -> creditService.check(command.customerId(), command.amount()));

    Future<CarrierCheckResult> carrierFuture =
        executor.submit(() -> carrierService.check(command.address()));

    return OrderCheckResult.merge(
        inventoryFuture.get(),
        creditFuture.get(),
        carrierFuture.get()
    );
}
```

并行后，请求耗时接近最慢的那个任务，而不是三个任务之和。这里的收益来自 IO 等待重叠，而不是 CPU 被神奇地加速。

## 多线程不适合什么

多线程不是默认选项。以下场景要谨慎：

- 任务之间有严格顺序，比如先扣库存再生成库存流水。
- 数据共享复杂，容易产生竞态。
- 单个任务非常小，线程切换成本超过收益。
- 下游系统已经限流，并发只会把压力打爆。
- 业务要求强事务一致性，不能拆成并发步骤。

比如订单扣库存不能简单把每个 SKU 丢给不同线程同时扣。如果一个订单内多个 SKU 需要同一个事务保证全部成功或全部失败，并行拆分反而会增加补偿复杂度。

## 落地判断标准

判断一个供应链流程是否适合多线程，可以按下面的顺序确认：

1. 是否存在互不依赖的子任务。订单详情聚合、库存报表查询、物流轨迹批量拉取通常适合。
2. 是否主要等待 IO。数据库、RPC、HTTP 调用占主导时，并发更容易产生收益。
3. 是否会修改同一份业务事实。库存余额、订单状态、付款状态这类数据必须先保证一致性。
4. 下游是否有容量限制。承运商接口、WMS 接口、数据库连接池都需要限流。
5. 失败结果能否被处理。查询类任务可以降级，交易类任务必须明确回滚或补偿。

多线程优化前后要记录耗时、吞吐、错误率、队列长度和下游压力。只看单次请求变快是不够的，系统还要在高峰流量下保持稳定。

## 小结

Java 多线程首先是一种工程手段，不是语法技巧。供应链系统使用多线程，核心收益是提升吞吐、缩短 IO 密集型流程耗时、让后台批处理更高效。使用前必须判断任务是否独立、是否共享状态、是否需要事务一致性。能并行的校验和查询可以并行，涉及最终库存和单据状态的数据修改必须保持清晰的事务边界。
