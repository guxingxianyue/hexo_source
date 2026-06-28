---
title: Java多线程基础：线程生命周期、创建方式和业务边界
date: 2016-03-05 20:47:08
tags: [Java, 多线程, 线程生命周期, 并发编程, 供应链系统]
---

Java 多线程基础要掌握三件事：线程处于什么状态、线程任务如何创建、线程之间如何协作。真正写业务代码时，还要判断哪些逻辑适合并发，哪些逻辑必须串行或依赖数据库事务保护。

## 线程生命周期

![Java 线程生命周期](/images/tech-flowcharts/java-thread-lifecycle-flow.svg)

Java 线程常见状态包括：

1. `NEW`：线程对象已创建，但还没有调用 `start()`。
2. `RUNNABLE`：线程已经可以被 CPU 调度，可能正在运行，也可能等待时间片。
3. `BLOCKED`：等待进入 `synchronized` 临界区。
4. `WAITING`：无限期等待其他线程唤醒，例如 `Object.wait()`、`Thread.join()`。
5. `TIMED_WAITING`：有超时时间的等待，例如 `sleep()`、带超时的 `wait()`。
6. `TERMINATED`：线程执行结束。

需要注意：调用 `start()` 后，线程不一定立即执行；调用 `run()` 只是普通方法调用，不会启动新线程。

## 创建线程的常见方式

直接继承 `Thread`：

```java
class InventorySyncThread extends Thread {
    @Override
    public void run() {
        syncInventory();
    }
}
```

实现 `Runnable`：

```java
class InventorySyncTask implements Runnable {
    @Override
    public void run() {
        syncInventory();
    }
}
```

使用 `Callable` 获取返回值：

```java
Callable<Integer> task = () -> inventoryService.countLowStockSku();
FutureTask<Integer> futureTask = new FutureTask<>(task);
new Thread(futureTask).start();
Integer lowStockCount = futureTask.get();
```

生产代码中更推荐使用线程池，而不是直接 `new Thread()`：

```java
ExecutorService executor = Executors.newFixedThreadPool(8);
executor.submit(() -> inventoryService.syncByWarehouse("WH-SH"));
```

线程池可以控制并发数量、复用线程、设置队列和拒绝策略，更适合服务端应用。

## 供应链业务例子

库存同步任务可能要同步多个仓库：

```java
public void syncAllWarehouses(List<String> warehouseCodes) {
    List<CompletableFuture<Void>> futures = warehouseCodes.stream()
            .map(code -> CompletableFuture.runAsync(
                    () -> inventorySyncService.syncWarehouse(code),
                    inventoryExecutor
            ))
            .toList();

    CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();
}
```

这个场景适合并发，因为不同仓库之间通常可以独立同步。并发后整体耗时接近最慢的单个仓库，而不是所有仓库耗时相加。

但库存扣减不能只靠多线程提升速度。扣减涉及同一 SKU 的可用量、锁定量和库存流水，必须通过数据库条件更新、行锁或乐观锁保证一致性：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - #{qty},
    locked_qty = locked_qty + #{qty}
WHERE warehouse_id = #{warehouseId}
  AND sku_id = #{skuId}
  AND available_qty >= #{qty};
```

业务代码要根据影响行数判断是否预占成功。

## sleep、wait、join 的区别

`sleep()` 让当前线程暂停一段时间，但不会释放已经持有的对象锁。

`wait()` 必须在 `synchronized` 内调用，会释放对象锁，等待其他线程 `notify()` 或 `notifyAll()`。

`join()` 用于等待另一个线程执行结束。

示例：

```java
Thread syncThread = new Thread(() -> inventorySyncService.syncWarehouse("WH-BJ"));
syncThread.start();
syncThread.join();
```

在业务系统里，更常用的是 `CountDownLatch`、`CompletableFuture`、线程池和消息队列，而不是直接操作 `wait/notify`。

## 常见风险

第一，线程过多。线程不是越多越快，线程数超过系统承载能力后，会导致上下文切换、内存压力、连接池耗尽。

第二，共享变量不安全。多个线程同时修改 `HashMap`、普通 `int` 或业务对象时，可能出现数据错乱。

第三，异常丢失。异步任务里的异常如果没有收集和记录，主流程可能误以为任务成功。

第四，业务一致性被破坏。订单状态、库存扣减、付款确认这类流程必须有明确事务边界。

## 小结

多线程基础不是背 API，而是理解线程状态、任务提交、协作方式和一致性边界。供应链系统中，仓库同步、物流轨迹拉取、报表计算适合并发；库存扣减、状态流转、财务结算必须优先保证一致性。
