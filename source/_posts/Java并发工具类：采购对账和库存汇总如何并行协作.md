---
title: Java并发工具类：采购对账和库存汇总如何并行协作
date: 2022-05-23 09:50:00
tags: [Java, CountDownLatch, Semaphore, CompletableFuture, 供应链系统]
---

Java 并发工具类解决的是线程之间的协作问题。供应链系统里，很多流程不是简单加锁，而是多个任务并行执行后汇总结果，或者限制同时访问某个下游系统的并发量。常用工具包括 `CountDownLatch`、`Semaphore`、`CompletableFuture`。

## 工具选择流程

![Java 并发工具选择流程](/images/tech-flowcharts/concurrency-tools-selection-flow.svg)

## CountDownLatch：等待多个任务完成

采购对账时，需要同时加载三类数据：

- 采购入库单。
- 供应商发票。
- 付款记录。

三类数据查询互不依赖，可以并行查询，最后汇总差异。

```java
public ReconcileResult reconcile(long supplierId, LocalDate month) throws InterruptedException {
    CountDownLatch latch = new CountDownLatch(3);

    AtomicReference<List<Receipt>> receiptsRef = new AtomicReference<>();
    AtomicReference<List<Invoice>> invoicesRef = new AtomicReference<>();
    AtomicReference<List<Payment>> paymentsRef = new AtomicReference<>();

    executor.execute(() -> {
        try {
            receiptsRef.set(receiptService.query(supplierId, month));
        } finally {
            latch.countDown();
        }
    });

    executor.execute(() -> {
        try {
            invoicesRef.set(invoiceService.query(supplierId, month));
        } finally {
            latch.countDown();
        }
    });

    executor.execute(() -> {
        try {
            paymentsRef.set(paymentService.query(supplierId, month));
        } finally {
            latch.countDown();
        }
    });

    latch.await();
    return reconcileEngine.compare(receiptsRef.get(), invoicesRef.get(), paymentsRef.get());
}
```

这里的收益是缩短对账等待时间。原来三类数据串行查询，现在可以并行加载。

## Semaphore：限制并发访问下游

物流轨迹同步可能调用承运商 API。承运商接口有 QPS 限制，不能因为系统里有大量线程就无限请求。

```java
public class CarrierTrackClient {
    private final Semaphore semaphore = new Semaphore(20);

    public TrackInfo queryTrack(String trackingNo) {
        boolean acquired = false;
        try {
            acquired = semaphore.tryAcquire(1, 2, TimeUnit.SECONDS);
            if (!acquired) {
                throw new BizException("承运商接口繁忙，请稍后重试");
            }
            return doQuery(trackingNo);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new BizException("查询被中断");
        } finally {
            if (acquired) {
                semaphore.release();
            }
        }
    }
}
```

`Semaphore` 控制的是并发许可数。这里最多允许 20 个线程同时访问承运商接口，保护下游系统，也保护自己。

## CompletableFuture：异步编排更清晰

`CompletableFuture` 适合多个异步任务组合。订单详情页需要同时展示订单基础信息、库存状态、物流轨迹、应收金额：

```java
public OrderDetail detail(long orderId) {
    CompletableFuture<Order> orderFuture =
        CompletableFuture.supplyAsync(() -> orderService.get(orderId), executor);

    CompletableFuture<InventoryView> inventoryFuture =
        CompletableFuture.supplyAsync(() -> inventoryService.viewByOrder(orderId), executor);

    CompletableFuture<TrackInfo> trackFuture =
        CompletableFuture.supplyAsync(() -> trackService.queryByOrder(orderId), executor);

    CompletableFuture<Receivable> receivableFuture =
        CompletableFuture.supplyAsync(() -> financeService.receivable(orderId), executor);

    CompletableFuture.allOf(orderFuture, inventoryFuture, trackFuture, receivableFuture).join();

    return new OrderDetail(
        orderFuture.join(),
        inventoryFuture.join(),
        trackFuture.join(),
        receivableFuture.join()
    );
}
```

注意要传入业务线程池，不要默认依赖 `ForkJoinPool.commonPool()`，否则不同业务会混用同一个公共线程池，排查困难。

## 异常处理

异步任务一定要处理异常：

```java
CompletableFuture<TrackInfo> trackFuture =
    CompletableFuture
        .supplyAsync(() -> trackService.queryByOrder(orderId), executor)
        .exceptionally(e -> TrackInfo.empty("物流轨迹暂不可用"));
```

供应链系统的详情页通常允许部分信息降级，比如物流轨迹临时失败不应该导致整个订单详情不可用。但结算、扣库存这类核心流程不能随意吞异常。

## 选择建议

不同工具适合不同问题：

| 工具 | 解决的问题 | 供应链例子 |
| --- | --- | --- |
| `CountDownLatch` | 等待多个任务全部完成 | 采购对账同时加载入库单、发票、付款记录 |
| `Semaphore` | 控制同时访问数量 | 限制承运商轨迹接口并发 |
| `CompletableFuture` | 异步编排和结果聚合 | 订单详情并行查询库存、物流、财务 |
| `BlockingQueue` | 生产者消费者 | 仓储波次任务排队处理 |

选择工具时先描述线程之间的关系：是等待、限流、结果组合，还是任务排队。关系清楚了，工具选择通常就清楚了。不要为了使用高级 API 而把简单流程写复杂。

## 小结

并发工具类的价值是让线程协作更清晰。`CountDownLatch` 适合等待多个并行任务完成；`Semaphore` 适合限制下游并发；`CompletableFuture` 适合异步任务编排。供应链系统使用这些工具时，必须区分查询类流程和交易类流程：查询可以并行和降级，交易必须保证状态一致、异常可追踪。
