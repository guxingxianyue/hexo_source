---
title: GC对象判定与回收算法：订单批处理对象如何被回收
date: 2023-06-13 09:50:00
tags: [Java, JVM, GC, 回收算法, 供应链系统]
---

GC 的第一步不是回收，而是判断哪些对象还活着。只有理解对象存活判定、引用类型和基础回收算法，才能解释为什么某些对象明明业务上已经不用了，却仍然无法被回收，也才能写出对批处理和高并发服务更友好的代码。

## 整体流程图

![GC 对象判定与回收算法](/images/tech-flowcharts/gc-reachability-algorithm-flow.svg)

## 对象如何被判定为存活

主流 JVM 使用可达性分析判断对象是否存活。它从一组 GC Roots 出发，沿着引用链向下搜索，能被搜索到的对象就是存活对象，搜索不到的对象就是可回收对象。

常见 GC Roots 包括：

1. 虚拟机栈中局部变量引用的对象。
2. 方法区中类静态属性引用的对象。
3. 方法区中常量引用的对象。
4. Native 方法引用的对象。
5. 活跃线程对象、类加载器、同步锁持有对象等。

供应链服务中，一个订单导入任务创建了很多临时对象。如果这些对象只存在于方法局部变量里，任务结束后大概率可以被回收。但如果它们被放入静态集合、长生命周期缓存、线程本地变量中，就可能继续可达，导致内存无法释放。

## 订单批处理 Demo

下面是一个简化的订单导入任务：

```java
public class OrderImportJob {
    private final OrderRepository orderRepository;

    public void importOrders(List<OrderRow> rows) {
        List<OrderCommand> commands = new ArrayList<>(rows.size());

        for (OrderRow row : rows) {
            OrderCommand command = new OrderCommand(
                    row.getOrderNo(),
                    row.getSkuCode(),
                    row.getQuantity(),
                    row.getWarehouseCode()
            );
            commands.add(command);
        }

        orderRepository.batchCreate(commands);
    }
}
```

`commands` 是局部变量。`importOrders()` 执行结束后，如果 `batchCreate()` 没有把这些对象保存到全局结构里，这批 `OrderCommand` 对象就会失去可达路径，后续 GC 可以回收。

下面这种写法就有风险：

```java
public class BadOrderImportJob {
    private static final List<OrderCommand> HISTORY = new ArrayList<>();

    public void importOrders(List<OrderRow> rows) {
        for (OrderRow row : rows) {
            OrderCommand command = convert(row);
            HISTORY.add(command);
        }
    }
}
```

`HISTORY` 是静态字段，属于 GC Roots 可达链的一部分。只要进程不退出，列表里的历史订单命令就一直可达。业务上即使导入完成，内存也不会自动释放。这类问题在导入、导出、报表、对账任务里很常见。

## 引用类型

Java 引用可以分为四类：

1. 强引用：最常见，例如 `new OrderCommand()` 赋值给变量。只要强引用可达，GC 不会回收。
2. 软引用：内存不足时可能被回收，可用于对内存敏感的缓存，但现代服务更推荐使用成熟缓存组件并设置容量。
3. 弱引用：下一次 GC 发生时，只要没有强引用就会被回收，常见于 `WeakHashMap`。
4. 虚引用：不能通过引用拿到对象，主要用于跟踪对象回收状态。

供应链系统里不要简单依赖软引用实现核心缓存。库存、价格、路由规则这类数据更适合用 Caffeine、Redis、本地缓存加版本号等方式，并明确容量、过期和刷新策略。

## 基础回收算法

常见 GC 算法有三类：

1. 标记-清除：先标记可回收对象，再清除它们。问题是会产生内存碎片。
2. 标记-复制：把存活对象复制到另一块区域，再清理原区域。适合存活对象少的新生代。
3. 标记-整理：标记后把存活对象向一端移动，减少碎片。适合老年代。

JVM 分代回收的基本依据是弱分代假说：大多数对象朝生夕死，少数对象会长期存活。供应链接口里的请求 DTO、计算中间对象、临时报表行通常很快死亡，适合在新生代快速回收；缓存、连接池、规则表、单例服务通常会长期存活，最终进入老年代。

## 让 GC 更轻松的编码方式

GC 可以自动回收内存，但不能替开发者修正错误的引用关系。实践中要注意：

1. 批处理按批次提交并释放引用，不要把全量数据放进一个大集合。
2. 静态集合只放真正需要全局共享的数据，并设置上限。
3. `ThreadLocal` 使用后及时 `remove()`，尤其在线程池场景。
4. 缓存必须有容量和过期策略。
5. 大对象和大数组要谨慎，避免频繁进入老年代。

一个更稳妥的导入方式是分片处理：

```java
public void importOrders(Stream<OrderRow> rowStream) {
    List<OrderCommand> batch = new ArrayList<>(1000);
    rowStream.forEach(row -> {
        batch.add(convert(row));
        if (batch.size() == 1000) {
            orderRepository.batchCreate(batch);
            batch.clear();
        }
    });
    if (!batch.isEmpty()) {
        orderRepository.batchCreate(batch);
        batch.clear();
    }
}
```

这段代码把峰值对象数量限制在一个批次内，既降低堆内存压力，也减少 GC 扫描和复制的成本。对于订单导入、库存同步、仓储流水归档，这类批处理方式通常比一次性全量加载更稳定。
