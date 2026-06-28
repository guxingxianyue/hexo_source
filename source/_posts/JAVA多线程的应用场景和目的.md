---
title: Java多线程的应用场景和目的
date: 2016-03-20 21:03:08
tags: [Java, 多线程, 并发编程, 供应链系统]
---

Java 多线程的目的不是把代码写复杂，而是在合适的场景里提升吞吐、降低等待时间，并让 CPU、网络、磁盘和下游服务资源得到更充分的利用。是否应该使用多线程，关键不在于“会不会开线程”，而在于能否判断任务之间有没有依赖、瓶颈在哪里、并发后是否会破坏数据一致性。

## 整体流程

![Java 多线程业务处理流程](/images/tech-flowcharts/java-thread-business-flow.svg)

## 多线程解决的核心问题

多线程常见目标有三类：

1. 提升吞吐量：让系统在单位时间内处理更多任务。
2. 降低等待时间：把互不依赖的 IO 操作并行执行，缩短整体响应时间。
3. 提高资源利用率：当一个线程等待数据库、Redis、HTTP 接口时，其他线程可以继续执行。

但多线程不是默认答案。对于 CPU 密集型任务，线程数超过 CPU 核数太多会带来上下文切换；对于数据库密集型任务，线程过多可能把连接池和数据库压垮；对于共享数据修改，如果没有并发控制，会出现脏数据、重复扣减、状态错乱。

## 供应链场景：订单详情聚合

订单详情页通常需要展示订单基础信息、库存状态、物流轨迹、应收金额。它们来自不同模块，彼此没有强依赖：

```text
订单基础信息 -> OMS
库存状态     -> Inventory Service
物流轨迹     -> TMS
应收金额     -> Finance Service
```

如果串行执行，每个接口耗时都会累加：

```text
订单 30ms + 库存 40ms + 物流 80ms + 财务 50ms = 200ms
```

如果并行查询，整体耗时更接近最慢的那个任务：

```text
max(30ms, 40ms, 80ms, 50ms) + 聚合成本
```

示例代码：

```java
public OrderDetail queryOrderDetail(long orderId) {
    CompletableFuture<Order> orderFuture =
            CompletableFuture.supplyAsync(() -> orderService.get(orderId), bizExecutor);
    CompletableFuture<InventoryView> inventoryFuture =
            CompletableFuture.supplyAsync(() -> inventoryService.viewByOrder(orderId), bizExecutor);
    CompletableFuture<TrackInfo> trackFuture =
            CompletableFuture.supplyAsync(() -> trackService.query(orderId), bizExecutor);
    CompletableFuture<Receivable> receivableFuture =
            CompletableFuture.supplyAsync(() -> financeService.receivable(orderId), bizExecutor);

    CompletableFuture.allOf(orderFuture, inventoryFuture, trackFuture, receivableFuture).join();

    return new OrderDetail(
            orderFuture.join(),
            inventoryFuture.join(),
            trackFuture.join(),
            receivableFuture.join()
    );
}
```

这里的关键点是：这些查询互不依赖，且主要耗时在 IO 等待上，因此适合并行。

## 不适合并发的情况

下面这种库存扣减逻辑不能简单并行：

```java
public void reserveStock(String skuCode, int qty) {
    int available = inventoryRepository.queryAvailable(skuCode);
    if (available < qty) {
        throw new BizException("库存不足");
    }
    inventoryRepository.decreaseAvailable(skuCode, qty);
    inventoryRepository.increaseLocked(skuCode, qty);
}
```

如果多个线程同时读到相同库存，再分别扣减，就可能超卖。库存预占必须依赖数据库行锁、乐观锁、原子更新或 Redis Lua 等机制保护一致性：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - #{qty},
    locked_qty = locked_qty + #{qty}
WHERE sku_code = #{skuCode}
  AND available_qty >= #{qty};
```

再通过影响行数判断是否预占成功。

## 线程池必须受控

生产系统不要为每个请求随意 `new Thread()`。线程创建和销毁有成本，线程数量失控还会耗尽内存、连接池和下游接口容量。

推荐使用明确的业务线程池：

```java
ThreadPoolExecutor bizExecutor = new ThreadPoolExecutor(
        16,
        32,
        60,
        TimeUnit.SECONDS,
        new ArrayBlockingQueue<>(1000),
        new ThreadFactoryBuilder().setNameFormat("order-query-%d").build(),
        new ThreadPoolExecutor.CallerRunsPolicy()
);
```

线程池配置要结合业务压测结果。队列不能无限大，否则流量高峰时请求会堆积很久，用户看到的是长时间等待而不是快速失败。

## 判断是否使用多线程的 checklist

使用多线程前可以问几个问题：

1. 任务之间是否互不依赖。
2. 瓶颈是 IO 等待还是 CPU 计算。
3. 并发后是否会修改同一份业务数据。
4. 线程池、数据库连接池、HTTP 连接池是否有容量上限。
5. 失败后是否能降级、重试或返回部分结果。
6. 日志和监控能否定位每个异步任务的耗时和异常。

多线程的收益来自清晰的任务拆分和资源控制。对供应链系统来说，订单聚合查询、采购对账、物流轨迹同步、批量报表生成都可能受益于并发；库存扣减、状态流转、单据审核则必须优先保证一致性。
