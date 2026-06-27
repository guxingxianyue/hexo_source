---
title: Java内存结构：库存服务里的堆栈元空间
date: 2023-06-08 09:40:00
tags: [Java, JVM, 内存结构, 堆内存, 供应链系统]
---

Java 内存结构是理解 JVM 问题的基础。线上服务出现 OOM、线程数过高、接口偶发慢、GC 频繁时，如果分不清堆、栈、元空间和直接内存，就很难判断问题属于对象太多、线程太多、类太多，还是 Netty 这类框架使用的堆外内存太多。

## 整体流程图

![Java 内存结构流程](/images/tech-flowcharts/java-memory-structure-flow.svg)

## JVM 运行时数据区

JVM 运行时数据区可以从线程共享和线程私有两个角度理解：

1. 程序计数器：线程私有，记录当前线程执行到哪条字节码指令。
2. Java 虚拟机栈：线程私有，每次方法调用都会创建栈帧，保存局部变量表、操作数栈、返回地址等。
3. 本地方法栈：线程私有，为 Native 方法服务。
4. Java 堆：线程共享，绝大多数对象实例和数组都在这里分配，也是 GC 管理的重点区域。
5. 方法区：线程共享，在 HotSpot 里 JDK 8 之后主要由元空间承载，保存类元数据、常量、方法信息等。
6. 直接内存：不属于 JVM 运行时数据区规范的一部分，但大量框架会使用，例如 NIO、Netty、文件传输。

供应链服务里，订单对象、库存快照、分页结果、DTO 通常进入堆；每个请求线程都有自己的虚拟机栈；大量动态代理类、反射元数据会占用元空间；网关、消息队列客户端、RPC 框架可能使用直接内存。

## 库存查询 Demo

下面用一个库存查询例子说明堆和栈的关系：

```java
public class InventoryQueryService {
    private final InventoryRepository repository;

    public InventoryQueryService(InventoryRepository repository) {
        this.repository = repository;
    }

    public InventoryView query(String skuCode, String warehouseCode) {
        InventoryRecord record = repository.find(skuCode, warehouseCode);
        int available = record.getOnHand() - record.getLocked();
        return new InventoryView(skuCode, warehouseCode, available);
    }
}
```

当线程执行 `query()` 时：

1. `skuCode`、`warehouseCode`、`record`、`available` 这些局部变量引用或基本类型值保存在当前线程的栈帧里。
2. `InventoryRecord` 和 `InventoryView` 对象通常分配在堆上。
3. `InventoryQueryService.class`、方法元数据、常量池等类信息在元空间里。
4. 请求结束后，栈帧弹出，局部变量消失；如果返回对象不再被其他地方引用，后续 GC 可以回收它。

栈上的变量生命周期通常很短，堆上的对象生命周期由引用关系决定。理解这一点，才能解释为什么一个局部变量引用的大对象在方法结束后可以被回收，而放入静态集合或缓存后就可能长期占用内存。

## 对象在堆里的结构

HotSpot 中一个普通对象通常由三部分组成：

1. 对象头：保存 Mark Word、类型指针等信息。
2. 实例数据：业务字段，例如 `skuCode`、`warehouseCode`、`availableQty`。
3. 对齐填充：为了满足内存对齐要求。

以库存对象为例：

```java
public class InventoryView {
    private String skuCode;
    private String warehouseCode;
    private int availableQty;

    public InventoryView(String skuCode, String warehouseCode, int availableQty) {
        this.skuCode = skuCode;
        this.warehouseCode = warehouseCode;
        this.availableQty = availableQty;
    }
}
```

如果一次批量查询返回 100 万条库存视图，不只是 100 万个 `InventoryView` 对象占内存，里面引用的 `String`、字符数组、集合容器也会占内存。线上估算内存时不能只看字段数量，还要看对象图。

## 常见内存异常

不同内存区域对应不同异常：

```text
java.lang.OutOfMemoryError: Java heap space
java.lang.OutOfMemoryError: GC overhead limit exceeded
java.lang.OutOfMemoryError: Metaspace
java.lang.OutOfMemoryError: Direct buffer memory
java.lang.StackOverflowError
java.lang.OutOfMemoryError: unable to create native thread
```

供应链项目里的典型触发原因：

1. `Java heap space`：一次导出全量订单、库存快照缓存无限增长、消息堆积后一次性反序列化。
2. `Metaspace`：动态生成类过多，或者热部署环境 ClassLoader 泄漏。
3. `Direct buffer memory`：Netty、NIO、大文件传输使用堆外内存过多。
4. `StackOverflowError`：递归解析 BOM 物料树没有终止条件。
5. `unable to create native thread`：线程池无界增长，或者容器线程数限制太低。

## 业务实现建议

供应链系统经常面对大批量数据，内存结构设计要服务于吞吐和稳定性：

1. 分页处理订单、库存、出入库流水，不要一次性加载全量数据。
2. 缓存要设置容量、过期时间和淘汰策略，避免静态 Map 无限增长。
3. 大文件导入导出使用流式处理，避免整个文件读入堆内存。
4. 线程池大小要受控，因为每个线程都会消耗栈内存和操作系统资源。
5. 使用 Netty 或 NIO 时，要同时监控堆内存和直接内存。

Java 内存结构的学习目标，是能把业务对象、线程、类元数据、IO 缓冲区分别映射到对应内存区域，并据此判断问题的根因和优化方向。
